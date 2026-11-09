# État de validation

Mise à jour : **9 novembre 2026**, passage au déploiement sur AWS EKS avec Terraform.

## Exécuté et réussi

**Pile actuelle (EKS 1.35, Cilium 1.19.7, Kyverno 1.17.1)**, sur la machine de développement :

- 8 tests Python : chaîne frontend/API/catalog, routes de santé, 404, erreur amont 502 et robustesse des sondes de sécurité.
- Contrôle structurel `tools/validate.py` sur **40 ressources** : identités dédiées, RBAC borné, Default Deny dans les quatre namespaces, DNS UDP/TCP et contextes de sécurité.
- **Kyverno CLI 1.17.1** (même version que dans le cluster) : **60/60** résultats attendus, dont les dix configurations dangereuses et le Deployment privilégié rejeté par les règles auto-générées.
- **Terraform 1.16.7, provider AWS 6.72.0** : `fmt -check`, `validate`, et `terraform test` avec un AWS simulé (2 scénarios réussis) : API limitée à l'IP détectée, accès privé des nœuds, 3 sous-réseaux, version 1.35 en support standard, métadonnées des nœuds limitées à 1 saut, coéquipiers administrateurs.
- `tools/lab.py kubeconfig` simulé : la commande `aws eks update-kubeconfig` générée et le fichier ignoré par Git ont été vérifiés.

**Pile précédente (Kubernetes 1.33.1 sur k3s, Cilium 1.18.3 seul CNI, Kyverno 1.15.2)**, sur un vrai cluster dans la CI GitHub Actions :

- profil de base : **50/50 contrôles réussis** (DNS, flux autorisés, refus réseau par Service et par IP de pod, refus vers l'API Kubernetes, absence de jeton, RBAC HTTP 403 réels, rejets d'admission Kyverno, Deployment privilégié refusé) ;
- profil L7 : **51/51 contrôles réussis**, dont `GET /admin` refusé en HTTP 403 par Cilium.

Les manifests, politiques et tests n'ont pas changé depuis ce passage ; seules les versions des composants et la plateforme ont changé.

## Problèmes trouvés par la première exécution réelle, puis corrigés

| Problème | Correction |
|---|---|
| Pods sans réseau sur k3s (`failed to find plugin "bridge"`) : Cilium écrivait sa configuration CNI dans des dossiers que k3s ne lit pas | Chemins CNI standard ; `lab.py up` attend désormais CoreDNS pour détecter ce cas tout de suite |
| 3 tests d'admission en échec : les fixtures privilégiées combinaient `privileged: true` et `allowPrivilegeEscalation: false`, refusé par l'API Kubernetes elle-même **avant** Kyverno | Fixtures et Deployment de test rendus valides : le rejet vient bien de `zt-workload-baseline` |

## Non exécuté ici

- **`terraform apply` sur un vrai compte AWS** et **`lab.py up` / `test` sur EKS** : aucun identifiant AWS n'était disponible dans l'environnement de création. Le premier `apply` est donc aussi le premier test réel ; conserver les erreurs éventuelles pour les corriger.
- **Pile actuelle sur un vrai cluster dans la CI** : depuis le 9 novembre 2026 vers 18 h, GitHub refuse de démarrer les jobs du dépôt (aucun job créé, probablement le quota de minutes Actions du compte propriétaire). La CI est prête (k3s 1.35.5, Cilium 1.19.7, Kyverno 1.17.1) et rejouera les 50 + 51 contrôles dès que les jobs pourront démarrer.
- **Filtrage L7 sur EKS** : en chaînage avec le CNI d'AWS, le filtrage HTTP de Cilium n'est pas garanti par la documentation ; à constater.
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

Sur AWS, suivre le [guide](guide-aws.md) jusqu'à `python tools/lab.py test`. Joindre ensuite les rapports `artifacts/*.json` au dossier, avec la date et les versions utilisées. Conserver les échecs éventuels dans les preuves, puis documenter les corrections et la nouvelle exécution.
