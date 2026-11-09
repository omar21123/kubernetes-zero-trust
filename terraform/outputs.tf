# Valeurs affichées à la fin de `terraform apply` (et par `terraform output`).
# tools/lab.py les lit pour récupérer le kubeconfig.

output "public_ip" {
  description = "IP publique de la VM Kubernetes"
  value       = aws_eip.node.public_ip
}

output "ssh_private_key_path" {
  description = "Clé privée SSH correspondant à la clé publique envoyée à AWS"
  value       = trimsuffix(var.ssh_public_key_path, ".pub")
}

output "ssh_command" {
  description = "Se connecter à la VM"
  value       = "ssh -i ${trimsuffix(var.ssh_public_key_path, ".pub")} ubuntu@${aws_eip.node.public_ip}"
}

output "allowed_cidrs" {
  description = "Adresses autorisées par le pare-feu"
  value       = local.allowed_cidrs
}

output "next_step" {
  description = "Étape suivante"
  value       = "Depuis la racine du dépôt : python tools/lab.py kubeconfig (attendre 2 à 3 minutes que k3s s'installe)"
}
