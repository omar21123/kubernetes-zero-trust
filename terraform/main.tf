# Infrastructure AWS du laboratoire : UNE machine virtuelle (EC2) qui fait tourner
# Kubernetes (k3s). Tout le reste (Cilium, Kyverno, application) est installé
# ensuite par `python tools/lab.py up`.
#
# Ressources créées :
#   1. une paire de clés SSH        -> pour se connecter à la VM
#   2. un groupe de sécurité        -> pare-feu AWS : seule votre IP entre
#   3. une IP publique fixe (EIP)   -> l'adresse ne change pas après un redémarrage
#   4. la VM Ubuntu + k3s           -> le cluster Kubernetes (1 nœud)

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project = "kubernetes-zero-trust"
    }
  }
}

# ---------------------------------------------------------------- Lectures
# Les blocs "data" LISENT des informations existantes, ils ne créent rien.

# Votre IP publique, pour n'ouvrir le pare-feu qu'à vous.
data "http" "my_ip" {
  url = "https://checkip.amazonaws.com"
}

locals {
  allowed_cidrs = length(var.allowed_cidrs) > 0 ? var.allowed_cidrs : ["${chomp(data.http.my_ip.response_body)}/32"]
}

# Image Ubuntu 24.04 officielle (publiée par Canonical).
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"]

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"]
  }
}

# Réseau par défaut du compte AWS (existe déjà dans chaque région).
data "aws_vpc" "default" {
  default = true
}

# Zones où le type de VM choisi est disponible.
data "aws_ec2_instance_type_offerings" "available" {
  location_type = "availability-zone"

  filter {
    name   = "instance-type"
    values = [var.instance_type]
  }
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
  filter {
    name   = "availability-zone"
    values = data.aws_ec2_instance_type_offerings.available.locations
  }
  filter {
    name   = "default-for-az"
    values = ["true"]
  }
}

# ---------------------------------------------------------------- Ressources

# 1. Clé SSH : AWS reçoit seulement la clé PUBLIQUE.
resource "aws_key_pair" "lab" {
  key_name   = "zero-trust"
  public_key = file(pathexpand(var.ssh_public_key_path))
}

# 2. Pare-feu : SSH (22) et API Kubernetes (6443) depuis votre IP uniquement.
#    L'application n'est jamais exposée sur Internet : on utilise kubectl port-forward.
resource "aws_security_group" "node" {
  name        = "zero-trust-node"
  description = "SSH and Kubernetes API from allowed IPs only"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = local.allowed_cidrs
  }

  ingress {
    description = "Kubernetes API (kubectl, helm)"
    from_port   = 6443
    to_port     = 6443
    protocol    = "tcp"
    cidr_blocks = local.allowed_cidrs
  }

  egress {
    description = "Downloads: k3s, Helm charts, container images"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# 3. IP publique fixe.
resource "aws_eip" "node" {
  domain = "vpc"
  tags   = { Name = "zero-trust-k3s" }
}

# 4. La VM. Au premier démarrage, user_data installe k3s (cloud-init).
resource "aws_instance" "node" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = var.instance_type
  subnet_id              = sort(data.aws_subnets.default.ids)[0]
  vpc_security_group_ids = [aws_security_group.node.id]
  key_name               = aws_key_pair.lab.key_name

  user_data = templatefile("${path.module}/user-data.sh.tftpl", {
    public_ip      = aws_eip.node.public_ip
    install_script = file("${path.module}/../cluster/install-k3s.sh")
  })
  user_data_replace_on_change = true # modifier le script = recréer la VM

  root_block_device {
    volume_size = 30
    volume_type = "gp3"
    encrypted   = true # disque chiffré
  }

  # IMDSv2 obligatoire et limité à la VM : un pod ne peut pas lire les métadonnées AWS.
  metadata_options {
    http_tokens                 = "required"
    http_put_response_hop_limit = 1
  }

  tags = { Name = "zero-trust-k3s" }

  lifecycle {
    ignore_changes = [ami] # une nouvelle image Ubuntu ne doit pas détruire le cluster
  }
}

resource "aws_eip_association" "node" {
  instance_id   = aws_instance.node.id
  allocation_id = aws_eip.node.id
}
