# Architecture et frontières de confiance

## Composants

| Namespace | Workload | Identité complète | Fonction |
|---|---|---|---|
| `zt-edge` | frontend | `system:serviceaccount:zt-edge:frontend` | Présenter le catalogue via l'API |
| `zt-app` | api | `system:serviceaccount:zt-app:api` | Lire les articles du catalogue |
| `zt-data` | catalog | `system:serviceaccount:zt-data:catalog` | Servir un jeu de données HTTP fictif |
| `zt-app` | auditor | `system:serviceaccount:zt-app:auditor` | Lire un ConfigMap précis pour démontrer RBAC |
| `zt-untrusted` | probe | `system:serviceaccount:zt-untrusted:probe` | Simuler un autre tenant sans accès applicatif |
| `kube-system` | AWS VPC CNI, Cilium, CoreDNS, Hubble | Identités système | Réseau (IP du VPC pour les pods, politiques Cilium), résolution et observation |
| `kyverno` | Contrôleurs Kyverno | Identités système | Admission et rapports de conformité |

Les applications ne sont exposées que par des Services `ClusterIP`. Le frontend appelle `/catalog` sur l'API ; l'API appelle `/items` sur catalog. Les routes `/health` servent aux sondes. La route fictive `/admin` de l'API permet de comparer L4 et L7 sans opération sensible réelle.

## Frontières

1. **Entre namespaces** : les sélecteurs imposent à la fois un namespace et un label de pod. Changer uniquement le namespace ne suffit pas à obtenir une autorisation.
2. **Entre workloads du même namespace** : `auditor` et `api` ont des identités distinctes. Le premier ne bénéficie pas de la sortie réseau de l'API vers catalog.
3. **Entre plan applicatif et plan de contrôle** : seul auditor dispose d'une exception réseau vers l'API et d'un jeton projeté. RBAC borne les requêtes autorisées même si le réseau les laisse passer.
4. **Entre conteneur et hôte** : Restricted PSS, UID non root, seccomp RuntimeDefault, suppression des capabilities, interdiction de l'escalade et de hostPath.
5. **À l'entrée du cluster** : Kyverno vérifie les nouvelles configurations et les mises à jour. Les ressources historiques sont signalées par les rapports ; elles ne sont pas corrigées automatiquement.

Un namespace n'est pas une frontière de sécurité suffisante à lui seul. Les NetworkPolicies, RBAC et l'admission rendent les restrictions effectives.

## Hypothèses explicites

L'administrateur du laboratoire, l'API server, les nœuds, Cilium et Kyverno sont dans la base de confiance. L'attaquant initial peut exécuter du code dans un conteneur applicatif ou voler son jeton. Il n'est pas déjà administrateur du cluster.

Les ServiceAccounts applicatifs ne peuvent créer ni modifier des pods, des labels, des Services, des politiques ou du RBAC. Cette hypothèse empêche une application compromise de se faire passer pour une autre en créant un pod avec son label ou son ServiceAccount. Un utilisateur disposant de `create pods` peut généralement sélectionner une autre identité du namespace : ce droit doit rester une responsabilité de déploiement contrôlée.

Les identités ServiceAccount ne constituent pas une authentification HTTP entre services. Les NetworkPolicies Kubernetes de base utilisent les labels ; Cilium peut sélectionner l'identité ServiceAccount issue des métadonnées Kubernetes. Aucun certificat client applicatif n'est déployé.

## Ordre de déploiement

`terraform apply (IAM, cluster EKS, nœuds) → Cilium/Hubble en chaînage avec le CNI d'AWS → Kyverno → namespaces et identités → admission et politiques réseau → workloads → tests`.

Les pods démarrent après les protections. Aucun cluster existant de production n'est ciblé par les scripts. Les exclusions système de Kyverno sont limitées par une liste explicite de quatre namespaces ; retirer leur label `zero-trust` ne désactive donc pas les règles d'admission.
