"""Offline structural checks. This does not emulate Kyverno or a CNI."""
from pathlib import Path
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
NAMESPACES = {"zt-edge", "zt-app", "zt-data", "zt-untrusted"}


def load(directory):
    return [document for path in sorted((ROOT / directory).rglob("*.yaml"))
            for document in yaml.safe_load_all(path.read_text(encoding="utf-8")) if document]


def validate():
    docs = load("manifests") + load("policies")
    keys = [(d["apiVersion"], d["kind"], d["metadata"].get("namespace"), d["metadata"]["name"]) for d in docs]
    assert len(keys) == len(set(keys)), "Duplicate resource"
    assert {d["metadata"]["name"] for d in docs if d["kind"] == "Namespace"} == NAMESPACES
    accounts = {(d["metadata"]["namespace"], d["metadata"]["name"]) for d in docs if d["kind"] == "ServiceAccount"}
    for document in docs:
        kind, metadata, spec = document["kind"], document["metadata"], document.get("spec", {})
        if kind == "ServiceAccount":
            assert document["automountServiceAccountToken"] is False
        if kind == "Deployment":
            pod = spec["template"]["spec"]
            assert (metadata["namespace"], pod["serviceAccountName"]) in accounts
            assert pod["automountServiceAccountToken"] is False
            assert pod["securityContext"]["runAsNonRoot"] is True
            assert pod["securityContext"]["runAsUser"] > 0
            assert pod["securityContext"]["seccompProfile"]["type"] == "RuntimeDefault"
            assert all("hostPath" not in volume for volume in pod.get("volumes", []))
            for container in pod["containers"]:
                security = container["securityContext"]
                assert security["readOnlyRootFilesystem"] is True
                assert security["allowPrivilegeEscalation"] is False
                assert security["capabilities"] == {"drop": ["ALL"]}
                assert container["resources"]["limits"].keys() >= {"cpu", "memory"}
                assert container["resources"]["requests"].keys() >= {"cpu", "memory"}
            projected = [source for volume in pod.get("volumes", [])
                         for source in volume.get("projected", {}).get("sources", [])
                         if "serviceAccountToken" in source]
            assert bool(projected) == (metadata["name"] == "auditor")
            if projected:
                assert projected[0]["serviceAccountToken"]["expirationSeconds"] == 600
        if kind == "Role":
            assert document["rules"] == [{"apiGroups": [""], "resources": ["configmaps"],
                                          "resourceNames": ["public-info"], "verbs": ["get"]}]
        assert kind not in {"ClusterRole", "ClusterRoleBinding"}, "No workload cluster-wide RBAC is needed"
        if kind == "NetworkPolicy":
            for direction, peer_key in [("ingress", "from"), ("egress", "to")]:
                for rule in spec.get(direction, []):
                    assert rule.get(peer_key), "Unrestricted peer"
                    assert rule.get("ports"), "Unrestricted ports"
                    for peer in rule[peer_key]:
                        assert peer.get("namespaceSelector", {}).get("matchLabels"), "Namespace must be explicit"
                        assert peer.get("podSelector", {}).get("matchLabels"), "Pod identity must be explicit"
    denies = [d for d in docs if d["kind"] == "NetworkPolicy" and d["metadata"]["name"] == "default-deny"]
    assert {d["metadata"]["namespace"] for d in denies} == NAMESPACES
    for policy in denies:
        assert policy["spec"] == {"podSelector": {}, "policyTypes": ["Ingress", "Egress"]}
    dns = [d for d in docs if d["kind"] == "NetworkPolicy" and d["metadata"]["name"] == "allow-coredns"]
    assert {d["metadata"]["namespace"] for d in dns} == NAMESPACES
    for policy in dns:
        rule = policy["spec"]["egress"][0]
        assert {(p["protocol"], p["port"]) for p in rule["ports"]} == {("TCP", 53), ("UDP", 53)}
        assert rule["to"][0]["namespaceSelector"]["matchLabels"] == {"kubernetes.io/metadata.name": "kube-system"}
        assert rule["to"][0]["podSelector"]["matchLabels"] == {"k8s-app": "kube-dns"}
    policy = next(d for d in docs if d["kind"] == "ClusterPolicy")
    assert policy["spec"]["webhookConfiguration"]["failurePolicy"] == "Fail"
    for rule in policy["spec"]["rules"]:
        assert rule["validate"]["failureAction"] == "Enforce"
        assert set(rule["match"]["any"][0]["resources"]["namespaces"]) == NAMESPACES
    for path in (ROOT / "tests/fixtures").glob("*.yaml"):
        list(yaml.safe_load_all(path.read_text(encoding="utf-8")))
    print(f"OK: {len(docs)} ressources, identites, RBAC, Default Deny, DNS et securite des workloads.")


if __name__ == "__main__":
    try:
        validate()
    except (AssertionError, KeyError, yaml.YAMLError) as error:
        print(f"Validation echouee: {error}", file=sys.stderr)
        sys.exit(1)
