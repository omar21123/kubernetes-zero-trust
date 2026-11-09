# Contrôle des configurations avec Kyverno

Le projet installe un seul moteur d'admission et une seule ClusterPolicy métier : `zt-workload-baseline`. Elle cible explicitement les quatre namespaces du laboratoire. Les composants d'infrastructure restent hors de ce périmètre, car le CNI notamment a besoin de privilèges système.

La baseline PSS est figée à **v1.29**, acceptée par le validateur de Kyverno 1.17.1 et appliquée ici sur Kubernetes 1.35 (EKS). Il s'agit de la version du référentiel de sécurité, distincte de celle du serveur Kubernetes. Les contrôles demandés par le sujet sont couverts par ce référentiel.

## Contrat imposé

| Règle | Contrôle | Exemple de refus |
|---|---|---|
| `restricted-pod-security` | Pod Security Standards Restricted, version v1.29 | `privileged: true`, hostPath, hostNetwork, root, capabilities excessives, escalade |
| `explicit-identity` | ServiceAccount explicite différent de `default`, automount désactivé | Compte default ou jeton automatique |
| `immutable-root-and-bounded-resources` | Racine en lecture seule, requests et limits CPU/mémoire | `readOnlyRootFilesystem: false` ou ressources absentes |

Restricted comprend aussi le profil seccomp et la suppression des capabilities. Le troisième contrôle vérifie les conteneurs normaux et initContainers. Les ephemeralContainers sont couverts par les exigences PSS pertinentes mais n'acceptent pas tous les champs de ressources d'un conteneur normal ; la vérification requests/limits ne leur est donc pas appliquée. L'accès au sous-endpoint de débogage doit rester réservé aux opérateurs, et ne figure dans aucun RBAC applicatif.

Les policies PSS de Kyverno couvrent le socle Restricted sans réécrire manuellement chaque interdiction. L'auto-génération Kyverno doit appliquer ces règles aux templates des Deployments et autres contrôleurs reconnus ; un test serveur vérifie explicitement un Deployment privilégié.

`validate.failureAction: Enforce` rejette la configuration. `webhookConfiguration.failurePolicy: Fail` fait échouer l'admission si le webhook applicable ne répond pas correctement. Ce choix protège la cohérence mais impose d'exploiter Kyverno avec une disponibilité adaptée.

Le projet n'active pas en parallèle Pod Security Admission Restricted sur les namespaces : cela permet d'identifier les rejets Kyverno sans dupliquer la même baseline. Sur un cluster qui possède déjà PSA Restricted, un manifest dangereux peut être rejeté plus tôt ; le test pédagogique attend alors à tort la signature Kyverno. Utiliser le cluster EKS dédié créé par Terraform pour reproduire les preuves.

## Essais sans créer de ressources dangereuses

Les tests hors cluster peuvent d'abord être exécutés avec `kyverno test tests/kyverno --remove-color`. Ils vérifient les règles positives et négatives ainsi que leur auto-génération pour les Deployments. Ils ne remplacent pas les essais de webhook ci-dessous.

```console
kubectl create --dry-run=server -f tests/fixtures/safe.yaml
kubectl create --dry-run=server -f tests/fixtures/privileged.yaml
kubectl create --dry-run=server -f tests/fixtures/hostpath.yaml
kubectl create --dry-run=server -f tests/fixtures/capabilities.yaml
```

Le premier est accepté. Les autres doivent être refusés avec `zt-workload-baseline` et la règle concernée. Ce sont des résultats **attendus** ; les sorties observées seront enregistrées uniquement à l'exécution de `lab.py test`.

Les fixtures sont exclues du déploiement normal. Ne jamais exécuter un `kubectl apply -R -f .` à la racine du projet. Une erreur de syntaxe, un quota dépassé ou une indisponibilité du webhook ne constitue pas une preuve de détection de la configuration dangereuse : les tests exigent l'identification de la politique Kyverno.

## Contrôle continu et limites

`background: true` permet l'évaluation des objets existants. Consulter les PolicyReports avec `kubectl get policyreports -A`. Une violation historique signalée reste en place tant qu'un opérateur ne la corrige pas.

La baseline exige la présence des budgets CPU/mémoire mais n'impose pas de plafond par conteneur ; les ResourceQuotas limitent les budgets agrégés par namespace. Elle ne vérifie ni signature d'image, ni digest obligatoire, ni autorisation métier d'utiliser un ServiceAccount donné. La restriction de ces opérations repose ici sur l'absence de droit de création/modification de workloads pour les comptes applicatifs.
