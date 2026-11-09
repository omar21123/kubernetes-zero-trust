# État de validation

Mise à jour : **9 novembre 2026**, passage au déploiement AWS avec Terraform et k3s.

## Exécuté et réussi

**Hors cluster** (machine de développement et CI GitHub Actions, job `offline`) :

- 8 tests Python : chaîne frontend/API/catalog, routes de santé, 404, erreur amont 502 et robustesse des sondes de sécurité.
- Contrôle structurel `tools/validate.py` sur **40 ressources** : identités dédiées, RBAC borné, Default Deny dans les quatre namespaces, DNS UDP/TCP et contextes de sécurité.
- **Kyverno CLI 1.15.2** : Pods conformes, configurations dangereuses et règles auto-générées pour les Deployments.
- **Terraform** : `fmt -check`, `validate`, et `terraform test` avec un AWS simulé (détection de votre IP, choix du sous-réseau, IP fixe injectée dans le script de démarrage, commande SSH). Le script de démarrage généré passe `bash -n`.

**Sur un vrai cluster k3s** (CI GitHub Actions, job `integration`, Ubuntu 24.04) installé avec **le même script `cluster/install-k3s.sh`** que la VM AWS, puis `python tools/lab.py up` :

- profil de base : **50/50 contrôles réussis** (DNS, flux autorisés, refus réseau par Service et par IP de pod, refus vers l'API Kubernetes, absence de jeton, RBAC HTTP 403 réels, rejets d'admission Kyverno, Deployment privilégié refusé par les règles auto-générées) ;
- profil L7 : **51/51 contrôles réussis**, dont `GET /admin` refusé en HTTP 403 par Cilium.

Les rapports JSON sont disponibles dans l'artifact `zero-trust-results` de chaque exécution de la CI.

## Problèmes trouvés par la première exécution réelle, puis corrigés

| Problème | Correction |
|---|---|
| Pods sans réseau (`failed to find plugin "bridge" in path [/opt/cni/bin]`) : Cilium écrivait sa configuration CNI dans des dossiers que k3s ne lit pas | Chemins CNI par défaut dans `cluster/cilium-values.yaml` ; `lab.py up` attend désormais CoreDNS pour détecter ce cas tout de suite |
| 3 tests d'admission en échec : les fixtures privilégiées combinaient `privileged: true` et `allowPrivilegeEscalation: false`, refusé par l'API Kubernetes elle-même **avant** Kyverno | Fixtures et Deployment de test rendus valides (`allowPrivilegeEscalation: true`) : le rejet vient bien de `zt-workload-baseline` |

## Non exécuté ici

- **`terraform apply` sur un vrai compte AWS** : aucun identifiant AWS n'était disponible dans l'environnement de création. Le code est validé et testé avec un AWS simulé, et l'installation de k3s est testée en CI, mais la création réelle de la VM reste à constater lors de votre premier `apply`.
- Captures Hubble : à réaliser pendant la soutenance (voir [demonstrations.md](demonstrations.md)).

## Reproduire les vérifications

```console
python -m pip install -r requirements-dev.txt
python tools/validate.py
python -m unittest discover -s tests -v
kyverno test tests/kyverno --remove-color
terraform -chdir=terraform init
terraform -chdir=terraform validate
terraform -chdir=terraform test
```

Sur AWS, suivre le [guide](guide-aws.md) jusqu'à `python tools/lab.py test` et `python tools/lab.py test --l7`. Joindre ensuite les rapports `artifacts/*.json` au dossier, avec la date et les versions utilisées. Conserver les échecs éventuels dans les preuves, puis documenter les corrections et la nouvelle exécution.
