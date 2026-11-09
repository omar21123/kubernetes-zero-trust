# Démonstration et soutenance

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
