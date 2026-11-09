# Versions de Terraform et des "providers" (plugins) utilisés.
# `terraform init` télécharge ces plugins dans le dossier .terraform/.
terraform {
  required_version = ">= 1.7"

  required_providers {
    aws = {
      source  = "hashicorp/aws" # parle à l'API d'AWS
      version = "~> 6.0"
    }
    http = {
      source  = "hashicorp/http" # sert uniquement à trouver votre IP publique
      version = "~> 3.4"
    }
  }
}
