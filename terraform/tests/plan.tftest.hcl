# Test sans compte AWS : les réponses d'AWS sont simulées ("mock").
# Lancer : terraform -chdir=terraform test
mock_provider "aws" {
  mock_data "aws_vpc" {
    defaults = { id = "vpc-1" }
  }
  mock_data "aws_availability_zones" {
    defaults = { names = ["us-east-1a", "us-east-1b", "us-east-1c"] }
  }
  mock_data "aws_ec2_instance_type_offerings" {
    defaults = { locations = ["us-east-1a", "us-east-1b", "us-east-1c", "us-east-1d"] }
  }
  mock_data "aws_subnets" {
    defaults = { ids = ["subnet-d", "subnet-c", "subnet-b", "subnet-a"] }
  }
  mock_resource "aws_iam_role" {
    defaults = { arn = "arn:aws:iam::123456789012:role/mock" }
  }
  mock_resource "aws_launch_template" {
    defaults = { id = "lt-0123456789abcdef0", latest_version = 1 }
  }
}

mock_provider "http" {
  mock_data "http" {
    defaults = { response_body = "198.51.100.9\n" }
  }
}

run "eks" {
  command = apply

  assert {
    condition     = tolist(aws_eks_cluster.lab.vpc_config[0].public_access_cidrs) == tolist(["198.51.100.9/32"])
    error_message = "L'API doit être limitée à l'IP détectée"
  }
  assert {
    condition     = aws_eks_cluster.lab.vpc_config[0].endpoint_private_access
    error_message = "Les nœuds doivent joindre l'API par le réseau privé"
  }
  assert {
    condition     = tolist(aws_eks_cluster.lab.vpc_config[0].subnet_ids) == tolist(["subnet-a", "subnet-b", "subnet-c"])
    error_message = "Trois sous-réseaux triés attendus"
  }
  assert {
    condition     = aws_eks_cluster.lab.version == "1.35" && aws_eks_cluster.lab.upgrade_policy[0].support_type == "STANDARD"
    error_message = "Version en support standard attendue"
  }
  assert {
    condition     = aws_launch_template.nodes.metadata_options[0].http_put_response_hop_limit == 1
    error_message = "Les pods ne doivent pas joindre les métadonnées du nœud"
  }
  assert {
    condition     = length(aws_eks_access_entry.extra) == 0
    error_message = "Aucun admin supplémentaire par défaut"
  }
}

run "coequipiers" {
  command = plan

  variables {
    extra_admin_arns = ["arn:aws:iam::123456789012:user/alice"]
    allowed_cidrs    = ["203.0.113.10/32"]
  }

  assert {
    condition     = length(aws_eks_access_policy_association.extra) == 1
    error_message = "Le coéquipier doit être administrateur"
  }
  assert {
    condition     = tolist(aws_eks_cluster.lab.vpc_config[0].public_access_cidrs) == tolist(["203.0.113.10/32"])
    error_message = "allowed_cidrs doit remplacer l'IP détectée"
  }
}
