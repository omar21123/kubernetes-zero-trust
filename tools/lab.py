"""Cycle de vie du laboratoire sur le cluster k3s créé par Terraform dans AWS.

Ordre normal :
    terraform -chdir=terraform apply   # crée la VM et installe Kubernetes (k3s)
    python tools/lab.py kubeconfig     # récupère l'accès au cluster
    python tools/lab.py up             # installe Cilium, Kyverno puis l'application
    python tools/lab.py test           # démonstrations automatiques
    terraform -chdir=terraform destroy # supprime tout dans AWS
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
KUBECONFIG = ROOT / "zero-trust.kubeconfig"  # ignoré par Git : il donne un accès administrateur
CONTEXT = "zero-trust"
# Pile pédagogique figée (Kubernetes 1.33.1 : voir cluster/install-k3s.sh).
CILIUM = "1.18.3"
KYVERNO_CHART = "3.5.2"  # application Kyverno 1.15.2
NAMESPACES = ["zt-edge", "zt-app", "zt-data", "zt-untrusted"]
APP_FILES = ["app/server.py", "app/check.py", "app/audit.py"]
WORKLOADS = [("zt-edge", "frontend"), ("zt-app", "api"),
             ("zt-data", "catalog"), ("zt-app", "auditor"), ("zt-untrusted", "probe")]


def run(*args, check=True, timeout=180, input_text=None):
    command = [str(arg) for arg in args]
    result = subprocess.run(command, cwd=ROOT, input=input_text, text=True,
                            encoding="utf-8", errors="replace", capture_output=True,
                            timeout=timeout)
    if check and result.returncode:
        raise RuntimeError(f"{' '.join(command)}\n{result.stdout}{result.stderr}")
    return result


def k(*args, **kwargs):
    return run("kubectl", "--kubeconfig", KUBECONFIG, "--context", CONTEXT, *args, **kwargs)


def helm(*args, **kwargs):
    return run("helm", "--kubeconfig", KUBECONFIG, "--kube-context", CONTEXT, *args, **kwargs)


def apply(path):
    print(k("apply", "-f", path).stdout, end="")


def doctor():
    missing = [name for name in ("kubectl", "helm") if not shutil.which(name)]
    print("Python:", sys.version.split()[0])
    if missing:
        raise RuntimeError("Outils absents du PATH: " + ", ".join(missing))
    print(run("kubectl", "version", "--client").stdout.strip())
    print(run("helm", "version", "--short").stdout.strip())
    if not KUBECONFIG.exists():
        raise RuntimeError(f"{KUBECONFIG.name} absent. Lancer d'abord: python tools/lab.py kubeconfig")
    nodes = k("get", "nodes", "-o", "wide", check=False, timeout=30)
    if nodes.returncode:
        raise RuntimeError("API Kubernetes injoignable. VM demarree ? Votre IP a change ? "
                           "(relancer terraform apply)\n" + nodes.stderr)
    print(nodes.stdout, end="")


def fetch_kubeconfig():
    """Copie le kubeconfig de la VM AWS sur ce PC (SSH), en attendant la fin de l'installation de k3s."""
    if not shutil.which("terraform") or not shutil.which("scp"):
        raise RuntimeError("terraform et scp (OpenSSH) doivent etre dans le PATH")
    outputs = json.loads(run("terraform", "-chdir=terraform", "output", "-json").stdout)
    if "public_ip" not in outputs:
        raise RuntimeError("Aucune sortie Terraform. Lancer d'abord: terraform -chdir=terraform apply")
    address = outputs["public_ip"]["value"]
    key = Path(outputs["ssh_private_key_path"]["value"]).expanduser()
    print(f"Recuperation du kubeconfig depuis ubuntu@{address} (k3s s'installe en 2 a 3 minutes)...", flush=True)
    for attempt in range(40):
        result = run("scp", "-i", key, "-o", "StrictHostKeyChecking=accept-new", "-o", "ConnectTimeout=10",
                     f"ubuntu@{address}:zero-trust.kubeconfig", KUBECONFIG, check=False, timeout=60)
        if result.returncode == 0:
            print(f"OK: {KUBECONFIG.name} cree. Etape suivante: python tools/lab.py up")
            return
        print(f"  pas encore pret ({attempt + 1}/40), nouvel essai dans 15 s", flush=True)
        time.sleep(15)
    raise RuntimeError("Echec. Sur la VM, consulter: sudo tail -n 50 /var/log/cloud-init-output.log\n" + result.stderr)


def up():
    doctor()
    print("Installation de Cilium (reseau + NetworkPolicy) puis Kyverno (admission)...", flush=True)
    run("helm", "repo", "add", "cilium", "https://helm.cilium.io/", "--force-update")
    run("helm", "repo", "add", "kyverno", "https://kyverno.github.io/kyverno/", "--force-update")
    run("helm", "repo", "update", timeout=300)
    helm("upgrade", "--install", "cilium", "cilium/cilium", "--version", CILIUM,
         "--namespace", "kube-system", "-f", "cluster/cilium-values.yaml",
         "--wait", "--timeout", "10m", timeout=660)
    # Sans CNI le nœud est NotReady : il devient Ready une fois Cilium installé.
    k("wait", "--for=condition=Ready", "nodes", "--all", "--timeout=300s", timeout=330)
    # Preuve que les pods reçoivent bien un réseau : CoreDNS doit démarrer.
    k("rollout", "status", "deployment/coredns", "-n", "kube-system", "--timeout=300s", timeout=330)
    helm("upgrade", "--install", "kyverno", "kyverno/kyverno", "--version", KYVERNO_CHART,
         "--namespace", "kyverno", "--create-namespace",
         "-f", "cluster/kyverno-values.yaml", "--wait", "--timeout", "10m", timeout=660)
    deploy()


def ready():
    for namespace, deployment in WORKLOADS:
        k("rollout", "status", "deployment/" + deployment, "-n", namespace,
          "--timeout=180s", timeout=210)


def deploy():
    # Les contrôles sont installés AVANT qu'un pod applicatif puisse démarrer.
    for path in ["manifests/00-namespaces.yaml", "manifests/10-identities.yaml",
                 "manifests/20-quotas.yaml", "policies/admission/workload-baseline.yaml"]:
        apply(path)
    k("wait", "--for=condition=Ready", "clusterpolicy/zt-workload-baseline", "--timeout=120s")
    apply("policies/network")
    apply("policies/cilium")
    # deploy restaure le profil L3/L4 de base, y compris après une démonstration L7.
    k("delete", "cnp", "frontend-http-only", "-n", "zt-edge", "--ignore-not-found")
    # Pas d'image à construire : le code Python est publié dans un ConfigMap,
    # monté en lecture seule dans l'image officielle python.
    code_changed = False
    for namespace in NAMESPACES:
        files = [arg for path in APP_FILES for arg in ("--from-file", path)]
        manifest = k("create", "configmap", "app-code", "-n", namespace, *files,
                     "--dry-run=client", "-o", "yaml").stdout
        output = k("apply", "-f", "-", input_text=manifest).stdout
        print(output, end="")
        code_changed |= "configured" in output
    apply("manifests/30-workloads.yaml")
    if code_changed:
        for namespace, name in WORKLOADS:
            k("rollout", "restart", "deployment/" + name, "-n", namespace)
    ready()
    print("Deploiement termine. Lancer: python tools/lab.py test")


def exec_pod(namespace, name, *args):
    return k("exec", "-n", namespace, "deployment/" + name, "--", "python", *args)


def probe(namespace, name, mode, target):
    return exec_pod(namespace, name, "/app/check.py", mode, target)


def pod_ip(namespace, app):
    payload = json.loads(k("get", "pods", "-n", namespace, "-l", "app=" + app, "-o", "json").stdout)
    items = [item for item in payload["items"] if not item["metadata"].get("deletionTimestamp")
             and item["status"].get("phase") == "Running"]
    assert items, f"No running pod: {namespace}/{app}"
    return items[0]["status"]["podIP"]


def test_suite(l7=False):
    ready()  # A failing deployment must never produce a successful isolation report.
    results = []

    def record(name, operation):
        started = time.monotonic()
        try:
            response = operation()
            output = response.stdout + response.stderr if isinstance(response, subprocess.CompletedProcess) else str(response or "OK")
            passed = True
        except Exception as error:
            output, passed = str(error), False
        results.append({"name": name, "passed": passed, "seconds": round(time.monotonic() - started, 2), "output": output})
        print(("PASS " if passed else "FAIL ") + name, flush=True)

    # DNS checks and successful end-to-end calls are controls for the negative tests.
    for namespace, name in WORKLOADS:
        for mode in ["dns", "dns-tcp"]:
            record(f"{mode}: {name}", lambda ns=namespace, app=name, m=mode:
                   probe(ns, app, m, "api.zt-app.svc.cluster.local"))
    record("frontend -> api -> catalog", lambda: probe("zt-edge", "frontend", "allow", "http://127.0.0.1:8080/"))
    record("frontend -> api autorise", lambda: probe("zt-edge", "frontend", "allow", "http://api.zt-app:8080/catalog"))
    record("api -> catalog autorise", lambda: probe("zt-app", "api", "allow", "http://catalog.zt-data:8080/items"))

    for namespace, name, dest_ns, dest in [
        ("zt-edge", "frontend", "zt-data", "catalog"),
        ("zt-untrusted", "probe", "zt-edge", "frontend"),
        ("zt-untrusted", "probe", "zt-app", "api"),
        ("zt-untrusted", "probe", "zt-data", "catalog"),
        ("zt-data", "catalog", "zt-app", "api"),
    ]:
        record(f"{name} -> {dest} Service refuse", lambda ns=namespace, app=name, dn=dest_ns, d=dest:
               probe(ns, app, "deny", f"http://{d}.{dn}:8080/health"))
        record(f"{name} -> {dest} PodIP refuse", lambda ns=namespace, app=name, dn=dest_ns, d=dest:
               probe(ns, app, "deny", f"http://{pod_ip(dn, d)}:8080/health"))

    api_ip = k("get", "service", "kubernetes", "-n", "default", "-o", "jsonpath={.spec.clusterIP}").stdout
    for namespace, name in [("zt-edge", "frontend"), ("zt-app", "api")]:
        record(f"{name} -> apiserver refuse au reseau", lambda ns=namespace, app=name:
               probe(ns, app, "deny", f"https://{api_ip}:443/api"))
    for namespace, name in WORKLOADS:
        if name != "auditor":
            record(f"{name} sans jeton monte", lambda ns=namespace, app=name: exec_pod(ns, app, "-c",
                   "from pathlib import Path; assert not Path('/var/run/secrets/kubernetes.io/serviceaccount/token').exists(); "
                   "assert not Path('/var/run/zt-kubernetes/token').exists(); print('no mounted token')"))
    record("auditor: ConfigMap autorise et trois acces HTTP 403", lambda: exec_pod("zt-app", "auditor", "/app/audit.py"))

    def can_i(verb, resource, namespace, expected):
        account = "system:serviceaccount:zt-app:auditor"
        resource_args = [resource]
        if resource in {"pods/exec", "serviceaccounts/token"}:
            parent, subresource = resource.split("/", 1)
            resource_args = [parent, "--subresource=" + subresource]
        result = k("auth", "can-i", verb, *resource_args, "-n", namespace, "--as=" + account,
                   "--as-group=system:serviceaccounts", "--as-group=system:serviceaccounts:zt-app",
                   "--as-group=system:authenticated", check=False)
        assert result.stdout.strip() == expected and result.returncode == (0 if expected == "yes" else 1), \
            result.stdout + result.stderr
        return result

    for verb, resource, namespace, expected in [
        ("get", "configmap/public-info", "zt-app", "yes"),
        ("list", "secrets", "zt-app", "no"),
        ("create", "pods", "zt-app", "no"),
        ("create", "pods/exec", "zt-app", "no"),
        ("create", "serviceaccounts/token", "zt-app", "no"),
        ("create", "rolebindings", "zt-app", "no"),
        ("get", "pods", "zt-data", "no"),
    ]:
        record(f"RBAC auditor {verb} {resource} {namespace}: {expected}",
               lambda v=verb, r=resource, ns=namespace, e=expected: can_i(v, r, ns, e))

    def admission(path, should_allow):
        result = k("create", "--dry-run=server", "-f", path, check=False)
        if should_allow:
            assert result.returncode == 0, result.stdout + result.stderr
        else:
            assert result.returncode != 0 and "zt-workload-baseline" in result.stderr, \
                "Expected a Kyverno rejection, not an unrelated error:\n" + result.stdout + result.stderr
        return result

    record("admission: Pod conforme accepte", lambda: admission("tests/fixtures/safe.yaml", True))
    for path in sorted((ROOT / "tests/fixtures").glob("*.yaml")):
        if path.stem != "safe":
            record("admission refuse: " + path.stem, lambda p=path: admission(p, False))

    # Verify controller auto-generation, so dangerous Deployments fail at submission.
    def bad_deployment():
        payload = json.loads(k("get", "deployment", "api", "-n", "zt-app", "-o", "json").stdout)
        body = {"apiVersion": "apps/v1", "kind": "Deployment", "metadata": {"name": "bad-deployment", "namespace": "zt-app"},
                "spec": payload["spec"]}
        body["spec"]["template"]["spec"]["containers"][0]["securityContext"]["privileged"] = True
        result = k("create", "--dry-run=server", "-f", "-", input_text=json.dumps(body), check=False)
        assert result.returncode != 0 and "zt-workload-baseline" in result.stderr, result.stdout + result.stderr
        return result

    record("admission refuse Deployment privilegie (autogen)", bad_deployment)
    if l7:
        def l7_state():
            existing = json.loads(k("get", "networkpolicies", "-n", "zt-edge", "-o", "json").stdout)
            assert all(p["metadata"]["name"] != "frontend-to-api" for p in existing["items"]), "L4 allow still present"
            return k("get", "cnp", "frontend-http-only", "-n", "zt-edge")
        record("profil L7 actif sans autorisation L4 large", l7_state)
        record("L7 GET /admin refuse HTTP 403", lambda: probe("zt-edge", "frontend", "http403", "http://api.zt-app:8080/admin"))
    else:
        record("baseline GET /admin accessible par le frontend", lambda: probe("zt-edge", "frontend", "allow", "http://api.zt-app:8080/admin"))

    report = {"timestamp_utc": datetime.now(timezone.utc).isoformat(), "context": CONTEXT,
              "profile": "l7" if l7 else "baseline", "passed": all(r["passed"] for r in results), "checks": results}
    artifacts = ROOT / "artifacts"
    artifacts.mkdir(exist_ok=True)
    path = artifacts / ("integration-l7.json" if l7 else "integration.json")
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"{sum(r['passed'] for r in results)}/{len(results)} controles reussis. Rapport: {path}")
    if not report["passed"]:
        raise RuntimeError("Au moins un controle a echoue. Consulter le rapport.")


def l7_toggle(enabled):
    if enabled:
        apply("policies/optional/frontend-l7.yaml")
        k("delete", "networkpolicy", "frontend-to-api", "-n", "zt-edge", "--ignore-not-found")
        print("L7 active. Lancer test --l7; la convergence des politiques peut prendre quelques secondes.")
    else:
        apply("policies/network/application-flows.yaml")
        k("delete", "cnp", "frontend-http-only", "-n", "zt-edge", "--ignore-not-found")
        print("Baseline restauree.")


def main():
    commands = {"doctor": doctor, "kubeconfig": fetch_kubeconfig, "up": up, "deploy": deploy,
                "test": test_suite, "l7-on": lambda: l7_toggle(True), "l7-off": lambda: l7_toggle(False)}
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=commands)
    parser.add_argument("--l7", action="store_true", help="Verifier aussi le profil HTTP L7 (avec test)")
    args = parser.parse_args()
    if args.command == "test":
        test_suite(args.l7)
    else:
        commands[args.command]()


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, subprocess.TimeoutExpired, FileNotFoundError, AssertionError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
