#!/usr/bin/env bash
# Installe un petit Kubernetes (k3s) sur la machine de CI GitHub.
#
# Sert UNIQUEMENT à tester automatiquement les politiques du projet sur un vrai
# cluster gratuit à chaque push. Le laboratoire, lui, tourne sur AWS EKS (terraform/).
# Usage (en root) : KUBECONFIG_USER=runner bash tests/k3s/install-k3s.sh
set -euo pipefail

K3S_VERSION="${K3S_VERSION:-v1.35.5+k3s1}"   # Kubernetes 1.35, comme le cluster EKS
KUBECONFIG_USER="${KUBECONFIG_USER:-runner}"  # utilisateur qui reçoit le kubeconfig

args=(
  server
  --node-name=zero-trust
  --flannel-backend=none        # pas de réseau intégré : Cilium sera le CNI
  --disable-network-policy      # c'est Cilium qui applique les NetworkPolicy
  --disable=traefik             # pas d'Ingress dans ce projet
  --disable=servicelb           # pas de LoadBalancer
  --secrets-encryption          # Secrets chiffrés dans la base de k3s
)

curl -sfL https://get.k3s.io | INSTALL_K3S_VERSION="$K3S_VERSION" sh -s - "${args[@]}"

for _ in $(seq 60); do
  [[ -s /etc/rancher/k3s/k3s.yaml ]] && break
  sleep 2
done

# Kubeconfig avec le contexte "zero-trust", comme celui créé pour EKS.
home_dir="$(getent passwd "$KUBECONFIG_USER" | cut -d: -f6)"
target="$home_dir/zero-trust.kubeconfig"
sed -e 's/default$/zero-trust/' /etc/rancher/k3s/k3s.yaml > "$target"
chown "$KUBECONFIG_USER:" "$target"
chmod 600 "$target"
echo "k3s installé. kubeconfig : $target"
