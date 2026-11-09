# Références officielles

Références consultées lors de la conception le 2 novembre 2026. Les pages courantes peuvent décrire des versions plus récentes que la pile figée du laboratoire.

| Source | Utilisation dans le projet |
|---|---|
| [Kubernetes — Network Policies](https://kubernetes.io/docs/concepts/services-networking/network-policies/) | Isolation ingress/egress, permissions additives et sélecteurs |
| [Kubernetes — RBAC Good Practices](https://kubernetes.io/docs/concepts/security/rbac-good-practices/) | Moindre privilège et permissions d'escalade |
| [Kubernetes — Pod Security Standards](https://kubernetes.io/docs/concepts/security/pod-security-standards/) | Baseline Restricted, capabilities, hostPath et privilèges |
| [Kubernetes — Service Accounts](https://kubernetes.io/docs/concepts/security/service-accounts/) | Identités, jetons projetés et rotation |
| [Kubernetes — Multi-tenancy](https://kubernetes.io/docs/concepts/security/multi-tenancy/) | Limites des namespaces et isolation des tenants |
| [k3s — Installation](https://docs.k3s.io/installation/configuration) | Options du serveur k3s (CNI désactivé, chiffrement des Secrets) |
| [Terraform — provider AWS](https://registry.terraform.io/providers/hashicorp/aws/latest/docs) | Ressources EC2, groupe de sécurité, Elastic IP |
| [Cilium — Installation sur k3s](https://docs.cilium.io/en/stable/installation/k3s/) | Désactivation de flannel et de la NetworkPolicy intégrée de k3s |
| [Cilium — Exigences système v1.18](https://docs.cilium.io/en/v1.18/operations/system_requirements/) | Noyau et support eBPF |
| [Cilium — Policy Language](https://docs.cilium.io/en/stable/security/policy/language/) | Entités, sélecteurs d'identité et filtrage HTTP |
| [Cilium — Hubble Setup](https://docs.cilium.io/en/stable/observability/hubble/setup/) | Activation Relay/UI et observation des flux |
| [Cilium v1.18.3](https://github.com/cilium/cilium/releases/tag/v1.18.3) | Version de référence du laboratoire |
| [Kyverno — Validate Rules](https://kyverno.io/docs/policy-types/cluster-policy/validate/) | PSS, foreach, action Enforce et validation des workloads |
| [Kyverno — CRD v1.15.2](https://raw.githubusercontent.com/kyverno/kyverno/v1.15.2/config/crds/kyverno/kyverno.io_clusterpolicies.yaml) | Champs de configuration disponibles dans la version figée |
| [Kyverno — chart 3.5.2](https://raw.githubusercontent.com/kyverno/kyverno/kyverno-chart-3.5.2/charts/kyverno/Chart.yaml) | Correspondance chart 3.5.2 / application v1.15.2 |

La documentation récente marque ClusterPolicy comme déprécié au profit de nouvelles familles de politiques. Le laboratoire utilise explicitement l'API ClusterPolicy de Kyverno 1.15.2 ; une mise à niveau doit inclure la revue de cette migration et la réexécution des démonstrations.
