# Paramètres modifiables. Les valeurs par défaut conviennent pour le laboratoire.
# Pour en changer une : copier terraform.tfvars.example en terraform.tfvars.

variable "aws_region" {
  description = "Région AWS. AWS Academy Learner Lab : us-east-1 ou us-west-2."
  type        = string
  default     = "us-east-1"
}

variable "instance_type" {
  description = "Taille de la VM : t3.large = 2 vCPU et 8 Go de RAM."
  type        = string
  default     = "t3.large"
}

variable "ssh_public_key_path" {
  description = "Clé publique SSH créée avec ssh-keygen (la clé privée reste sur votre PC)."
  type        = string
  default     = "~/.ssh/zero-trust.pub"
}

variable "allowed_cidrs" {
  description = "Adresses autorisées à joindre SSH et l'API Kubernetes. Vide = votre IP actuelle."
  type        = list(string)
  default     = []
}
