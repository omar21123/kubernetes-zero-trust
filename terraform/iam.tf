# Identités AWS (IAM) : EKS et les nœuds ont chacun leur rôle, avec les seules
# politiques gérées par AWS dont ils ont besoin (moindre privilège).

# Rôle utilisé par le plan de contrôle EKS pour gérer le cluster.
resource "aws_iam_role" "cluster" {
  name = "zero-trust-eks-cluster"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "eks.amazonaws.com" }
      Action    = ["sts:AssumeRole", "sts:TagSession"]
    }]
  })
}

resource "aws_iam_role_policy_attachment" "cluster" {
  role       = aws_iam_role.cluster.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
}

# Rôle des VM workers : rejoindre le cluster, gérer les IP des pods, lire les images.
resource "aws_iam_role" "nodes" {
  name = "zero-trust-eks-nodes"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "nodes" {
  for_each = toset([
    "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy",          # rejoindre le cluster
    "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy",               # IP du VPC pour les pods
    "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly", # images système d'EKS
  ])
  role       = aws_iam_role.nodes.name
  policy_arn = each.value
}
