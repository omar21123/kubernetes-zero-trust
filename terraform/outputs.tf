# Valeurs affichées à la fin de `terraform apply` (et par `terraform output`).
# tools/lab.py les lit pour créer le kubeconfig.

output "cluster_name" {
  description = "Nom du cluster EKS"
  value       = aws_eks_cluster.lab.name
}

output "aws_region" {
  description = "Région du cluster"
  value       = var.aws_region
}

output "allowed_cidrs" {
  description = "Adresses autorisées à joindre l'API Kubernetes"
  value       = local.allowed_cidrs
}

output "next_step" {
  description = "Étape suivante"
  value       = "Depuis la racine du dépôt : python tools/lab.py kubeconfig, puis python tools/lab.py up"
}
