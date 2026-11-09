# Paramètres modifiables. Les valeurs par défaut conviennent pour le laboratoire.
# Pour en changer une : copier terraform.tfvars.example en terraform.tfvars.

variable "aws_region" {
  description = "Région AWS."
  type        = string
  default     = "us-east-1"
}

variable "kubernetes_version" {
  description = "Version Kubernetes d'EKS. Garder une version en support STANDARD (0,10 $/h) : une version en support étendu coûte 0,60 $/h."
  type        = string
  default     = "1.35"
}

variable "node_instance_type" {
  description = "Type des VM workers : t3.medium = 2 vCPU et 4 Go de RAM."
  type        = string
  default     = "t3.medium"
}

variable "node_count" {
  description = "Nombre de nœuds workers."
  type        = number
  default     = 2
}

variable "allowed_cidrs" {
  description = "Adresses autorisées à joindre l'API Kubernetes. Vide = votre IP actuelle."
  type        = list(string)
  default     = []
}

variable "extra_admin_arns" {
  description = "ARN d'utilisateurs IAM supplémentaires (coéquipiers) à rendre administrateurs du cluster."
  type        = list(string)
  default     = []
}
