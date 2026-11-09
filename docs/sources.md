# Références officielles

Références consultées lors de la conception (2 novembre 2026) et du passage à EKS (9 novembre 2026). Les pages courantes peuvent décrire des versions plus récentes que la pile figée du laboratoire.

| Source | Utilisation dans le projet |
|---|---|
| [Kubernetes — Network Policies](https://kubernetes.io/docs/concepts/services-networking/network-policies/) | Isolation ingress/egress, permissions additives et sélecteurs |
| [Kubernetes — RBAC Good Practices](https://kubernetes.io/docs/concepts/security/rbac-good-practices/) | Moindre privilège et permissions d'escalade |
| [Kubernetes — Pod Security Standards](https://kubernetes.io/docs/concepts/security/pod-security-standards/) | Baseline Restricted, capabilities, hostPath et privilèges |
| [Kubernetes — Service Accounts](https://kubernetes.io/docs/concepts/security/service-accounts/) | Identités, jetons projetés et rotation |
| [Kubernetes — Multi-tenancy](https://kubernetes.io/docs/concepts/security/multi-tenancy/) | Limites des namespaces et isolation des tenants |
| [Amazon EKS — versions Kubernetes](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html) | Calendrier du support standard et étendu (version 1.35) |
| [Amazon EKS — tarifs](https://aws.amazon.com/eks/pricing/) | 0,10 $/h en support standard, 0,60 $/h en support étendu |
| [Terraform — provider AWS](https://registry.terraform.io/providers/hashicorp/aws/latest/docs) | `aws_eks_cluster`, `aws_eks_node_group`, rôles IAM, launch template |
| [Cilium — AWS VPC CNI (chaînage)](https://docs.cilium.io/en/stable/installation/cni-chaining-aws-cni/) | Installation de Cilium derrière le CNI d'AWS |
| [k3s — Installation](https://docs.k3s.io/installation/configuration) | Cluster de test de la CI (CNI désactivé, chiffrement des Secrets) |
| [Cilium — Exigences système v1.18](https://docs.cilium.io/en/v1.18/operations/system_requirements/) | Noyau et support eBPF |
| [Cilium — Policy Language](https://docs.cilium.io/en/stable/security/policy/language/) | Entités, sélecteurs d'identité et filtrage HTTP |
| [Cilium — Hubble Setup](https://docs.cilium.io/en/stable/observability/hubble/setup/) | Activation Relay/UI et observation des flux |
| [Cilium v1.19.7](https://github.com/cilium/cilium/releases/tag/v1.19.7) | Version de référence du laboratoire (testée avec Kubernetes 1.32 à 1.35) |
| [Kyverno — Validate Rules](https://kyverno.io/docs/policy-types/cluster-policy/validate/) | PSS, foreach, action Enforce et validation des workloads |
| [Kyverno — CRD v1.17.1](https://raw.githubusercontent.com/kyverno/kyverno/v1.17.1/config/crds/kyverno/kyverno.io_clusterpolicies.yaml) | Champs de configuration disponibles dans la version figée |
| [Kyverno — chart 3.7.1](https://raw.githubusercontent.com/kyverno/kyverno/kyverno-chart-3.7.1/charts/kyverno/Chart.yaml) | Correspondance chart 3.7.1 / application v1.17.1 |

La documentation récente marque ClusterPolicy comme déprécié au profit de nouvelles familles de politiques. Le laboratoire utilise explicitement l'API ClusterPolicy, toujours prise en charge par Kyverno 1.17.1 ; une mise à niveau doit inclure la revue de cette migration et la réexécution des démonstrations.
