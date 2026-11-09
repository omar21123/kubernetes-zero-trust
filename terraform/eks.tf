# Le cluster Kubernetes managé (EKS) et ses nœuds workers.
#
# Coût indicatif (us-east-1) : plan de contrôle 0,10 $/h + 2 x t3.medium 0,083 $/h
# + IP publiques et disques ~0,01 $/h = environ 0,20 $/h. Toujours finir par
# `terraform -chdir=terraform destroy`.

resource "aws_eks_cluster" "lab" {
  name     = "zero-trust"
  version  = var.kubernetes_version
  role_arn = aws_iam_role.cluster.arn

  vpc_config {
    subnet_ids              = local.subnet_ids
    endpoint_public_access  = true                # kubectl depuis votre PC...
    public_access_cidrs     = local.allowed_cidrs # ...mais uniquement depuis votre IP
    endpoint_private_access = true                # les nœuds passent par le réseau privé
  }

  # Accès à l'API Kubernetes par identité AWS : celui qui lance Terraform est admin.
  access_config {
    authentication_mode                         = "API"
    bootstrap_cluster_creator_admin_permissions = true
  }

  # Ne jamais basculer automatiquement vers le support étendu payant (0,60 $/h).
  upgrade_policy {
    support_type = "STANDARD"
  }

  depends_on = [aws_iam_role_policy_attachment.cluster]
}

# Coéquipiers administrateurs (optionnel, variable extra_admin_arns).
resource "aws_eks_access_entry" "extra" {
  for_each      = toset(var.extra_admin_arns)
  cluster_name  = aws_eks_cluster.lab.name
  principal_arn = each.value
}

resource "aws_eks_access_policy_association" "extra" {
  for_each      = toset(var.extra_admin_arns)
  cluster_name  = aws_eks_cluster.lab.name
  principal_arn = each.value
  policy_arn    = "arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy"

  access_scope {
    type = "cluster"
  }

  depends_on = [aws_eks_access_entry.extra]
}

# Modèle des VM workers : disque chiffré, et métadonnées AWS (IMDSv2) limitées
# à 1 saut réseau pour qu'un pod ne puisse pas voler les identifiants du nœud.
resource "aws_launch_template" "nodes" {
  name_prefix = "zero-trust-nodes-"

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 1
  }

  block_device_mappings {
    device_name = "/dev/xvda"
    ebs {
      volume_size           = 20
      volume_type           = "gp3"
      encrypted             = true
      delete_on_termination = true
    }
  }

  tag_specifications {
    resource_type = "instance"
    tags          = { Name = "zero-trust-node" }
  }
}

resource "aws_eks_node_group" "nodes" {
  cluster_name    = aws_eks_cluster.lab.name
  node_group_name = "zero-trust-nodes"
  node_role_arn   = aws_iam_role.nodes.arn
  subnet_ids      = local.subnet_ids
  ami_type        = "AL2023_x86_64_STANDARD" # Amazon Linux 2023 optimisé pour EKS
  instance_types  = [var.node_instance_type]
  capacity_type   = "ON_DEMAND"

  scaling_config {
    desired_size = var.node_count
    min_size     = 1
    max_size     = var.node_count
  }

  update_config {
    max_unavailable = 1
  }

  launch_template {
    id      = aws_launch_template.nodes.id
    version = aws_launch_template.nodes.latest_version
  }

  depends_on = [aws_iam_role_policy_attachment.nodes]
}
