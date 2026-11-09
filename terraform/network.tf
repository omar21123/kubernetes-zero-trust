# Réseau : on réutilise le VPC par défaut du compte (déjà présent dans chaque région).
# Les nœuds sont dans des sous-réseaux publics : pas de NAT Gateway, donc pas de
# surcoût (environ 0,045 $/h). Ils ne sont pas joignables pour autant : le groupe
# de sécurité créé par EKS n'accepte que le trafic interne au cluster.
#
# Les blocs "data" LISENT des informations existantes, ils ne créent rien.

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project = "kubernetes-zero-trust"
    }
  }
}

# Votre IP publique : seule autorisée à joindre l'API Kubernetes.
data "http" "my_ip" {
  url = "https://checkip.amazonaws.com"
}

data "aws_vpc" "default" {
  default = true
}

# Zones de disponibilité utilisables par EKS (quelques zones ne le sont pas).
data "aws_availability_zones" "eks" {
  state            = "available"
  exclude_zone_ids = ["use1-az3", "usw1-az2", "cac1-az3"]
}

# Zones où le type de VM des nœuds est proposé.
data "aws_ec2_instance_type_offerings" "nodes" {
  location_type = "availability-zone"

  filter {
    name   = "instance-type"
    values = [var.node_instance_type]
  }
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
  filter {
    name   = "default-for-az"
    values = ["true"]
  }
  filter {
    name   = "availability-zone"
    values = setintersection(data.aws_availability_zones.eks.names, data.aws_ec2_instance_type_offerings.nodes.locations)
  }
}

locals {
  allowed_cidrs = length(var.allowed_cidrs) > 0 ? var.allowed_cidrs : ["${chomp(data.http.my_ip.response_body)}/32"]
  # EKS exige au moins deux zones ; trois suffisent largement.
  subnet_ids = slice(sort(data.aws_subnets.default.ids), 0, min(3, length(data.aws_subnets.default.ids)))
}
