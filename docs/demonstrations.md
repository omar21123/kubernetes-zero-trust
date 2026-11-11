# Démonstration et soutenance

## Démo en direct : le jour J

Recréer l'architecture prend environ 25 minutes (Terraform ≈ 14 min, `lab.py up` ≈ 5 à 8 min) : tout est prêt **avant** de passer devant le jury, et la démo elle-même dure environ 5 minutes.

**À faire depuis le réseau où aura lieu la démo.** L'API du cluster n'accepte que l'adresse IP détectée au moment de `terraform apply`. Si l'IP change (autre Wi-Fi, partage de connexion), `kubectl` échoue : relancer `terraform -chdir=terraform apply`, qui met à jour l'adresse autorisée en quelques minutes. Pour autoriser deux réseaux à l'avance, renseigner `allowed_cidrs` dans `terraform/terraform.tfvars` (une adresse `/32` par réseau).

| Quand | Commande (PowerShell, à la racine du dépôt) | Durée |
|---|---|---|
| T − 40 min | `git pull` puis `aws sts get-caller-identity` (doit afficher `TerraformUser`) | 1 min |
| T − 40 min | `terraform -chdir=terraform apply` puis `yes` | ≈ 14 min |
| T − 25 min | `python tools/lab.py kubeconfig` (nouveau cluster = nouveau kubeconfig) | 10 s |
| T − 25 min | `$env:KUBECONFIG = "$PWD\zero-trust.kubeconfig"` puis `python tools/lab.py up` | 5 à 8 min |
| T − 15 min | `python tools/lab.py test` : 50/50, et des flux à montrer dans Hubble | 3 min |
| T − 10 min | Terminal 2 : `kubectl -n zt-edge port-forward service/frontend 8080:8080`, ouvrir http://localhost:8080 | — |
| T − 10 min | Terminal 3 : `kubectl -n kube-system port-forward service/hubble-ui 12000:80`, ouvrir http://localhost:12000 | — |
| **Démo** | Terminal 1 : `python tools/lab.py demo` (Entrée entre chaque étape) | ≈ 5 min |
| Après | `terraform -chdir=terraform destroy` puis `yes` | ≈ 11 min |

`python tools/lab.py demo` affiche chaque commande avant de l'exécuter, puis dit si le résultat est celui attendu :

1. le cluster, les 5 workloads, les 12 NetworkPolicy et la ClusterPolicy ;
2. l'application : frontend → api → catalog ;
3. **démonstration 1** : frontend → catalog et probe → api bloqués (à montrer aussi dans Hubble), api → catalog autorisé ;
4. **démonstration 2** : aucun jeton dans le frontend, `audit.py` (200 puis 403), `kubectl auth can-i` ;
5. **démonstration 3** : `kubectl apply` d'un pod privilégié et d'un pod `hostPath`, refusés par Kyverno ; un pod conforme accepté ;
6. `terraform plan` : « No changes », l'infrastructure correspond au code.

Plan de secours : si le cluster ne peut pas être joint le jour J, présenter les captures du rapport et la sortie de `python tools/lab.py test` de la répétition. Coût : ≈ 0,50 $ par séance, à condition de lancer `destroy` juste après.

## Déroulé manuel, commande par commande

Ce déroulé couvre les quatre preuves demandées. Prévoir 10 à 15 minutes après le déploiement. Les statuts ci-dessous sont des résultats attendus, pas des captures d'une exécution déjà réalisée.

## 1. Montrer l'état et le fonctionnement nominal

```console
kubectl get pods -A
kubectl get networkpolicies -A
kubectl get clusterpolicy zt-workload-baseline
kubectl -n zt-edge exec deployment/frontend -- python /app/check.py allow http://127.0.0.1:8080/
```

Attendu : pods disponibles, ClusterPolicy Ready, JSON contenant le catalogue obtenu par frontend → api → catalog. Le loopback ne vérifie pas l'ingress du frontend ; la réponse complète exerce les deux communications inter-namespaces.

## 2. Prouver un refus réseau

Dans Hubble UI, sélectionner `zt-edge`. Exécuter :

```console
kubectl -n zt-edge exec deployment/frontend -- python /app/check.py dns catalog.zt-data.svc.cluster.local
kubectl -n zt-edge exec deployment/frontend -- python /app/check.py deny http://catalog.zt-data:8080/items
kubectl -n zt-app exec deployment/api -- python /app/check.py allow http://catalog.zt-data:8080/items
```

Attendu : DNS fonctionne ; l'accès direct frontend → catalog échoue ; l'accès api → catalog réussit. Corréler l'échec avec un flux Hubble `DROPPED` / refus de politique. Un timeout seul ne prouve pas que la NetworkPolicy en est la cause.

Le namespace non autorisé est testé avec :

```console
kubectl -n zt-untrusted exec deployment/probe -- python /app/check.py deny http://api.zt-app:8080/health
```

Le script complet teste également les PodIP pour exclure une simple défaillance de Service.

## 3. Prouver un refus RBAC depuis le workload

```console
kubectl -n zt-app exec deployment/auditor -- python /app/audit.py
```

| Requête authentifiée par auditor | Réponse attendue |
|---|---|
| GET `zt-app/configmaps/public-info` | 200 |
| GET `zt-app/configmaps/other-info` | 403 |
| GET liste `zt-app/secrets` | 403 |
| GET liste `zt-data/pods` | 403 |

Le premier succès prouve que DNS, TLS et authentification fonctionnent. Le 403 de `other-info` illustre le moindre privilège au niveau d'une ressource nommée, pas seulement d'un namespace. Le test ne révèle aucun secret.

## 4. Prouver le rejet d'une configuration dangereuse

```console
kubectl create --dry-run=server -f tests/fixtures/safe.yaml
kubectl create --dry-run=server -f tests/fixtures/privileged.yaml
kubectl create --dry-run=server -f tests/fixtures/hostpath.yaml
kubectl create --dry-run=server -f tests/fixtures/privilege-escalation.yaml
```

Attendu : le Pod conforme est accepté en dry-run, les autres sont rejetés par `zt-workload-baseline`. Aucun pod dangereux n'est lancé. Les autres fixtures couvrent SYS_ADMIN, root, filesystem accessible en écriture, compte default, jeton automatique, hostNetwork et initContainer privilégié.

## 5. Présenter le blast radius

Prendre le cas d'un frontend compromis : accès au processus et aux données locales, accès à l'API applicative, aucun accès direct à catalog ni à l'API Kubernetes, aucun jeton monté. Un attaquant peut toutefois exploiter les appels autorisés de l'API, puis tenter une seconde compromission. Montrer le tableau de [l'analyse](blast-radius.md) et expliquer cette propagation transitive.

## 6. Extension L7 facultative

```console
# Le profil de base autorise les chemins HTTP sur le port autorisé.
kubectl -n zt-edge exec deployment/frontend -- python /app/check.py allow http://api.zt-app:8080/admin
python tools/lab.py l7-on
python tools/lab.py test --l7
python tools/lab.py l7-off
```

Attendu avec L7 : `/catalog` reste accessible, `/admin` reçoit HTTP 403. En cas de convergence encore en cours, consulter Hubble et relancer le contrôle après stabilisation ; ne pas masquer un échec dans le rapport.

## Conserver les preuves

```console
python tools/lab.py test
```

Conserver `artifacts/integration.json`, les captures Hubble et les sorties d'admission. Ajouter la date, les versions réellement utilisées et les écarts constatés. Le job GitHub Actions publie les rapports sous l'artifact `zero-trust-results`. Aucun résultat simulé n'est fourni comme preuve réelle.
