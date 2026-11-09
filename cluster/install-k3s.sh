#!/usr/bin/env bash
# Installe Kubernetes (distribution k3s) sur une machine Ubuntu.
#
# Utilisé à deux endroits :
#   - par Terraform, au premier démarrage de la VM AWS (voir terraform/user-data.sh.tftpl) ;
#   - par la CI GitHub, pour tester exactement la même installation.
#
# Le nœud reste "NotReady" à la fin du script : c'est normal, il attend le réseau
# Cilium que `python tools/lab.py up` installe ensuite depuis votre PC.
set -euo pipefail

K3S_VERSION="${K3S_VERSION:-v1.33.1+k3s1}"       # Kubernetes 1.33.1
PUBLIC_IP="${PUBLIC_IP:-}"                        # IP utilisée par kubectl depuis votre PC
KUBECONFIG_USER="${KUBECONFIG_USER:-ubuntu}"      # utilisateur Linux qui reçoit le kubeconfig

args=(
  server
  --node-name=zero-trust
  --flannel-backend=none        # pas de réseau intégré : Cilium sera le CNI
  --disable-network-policy      # c'est Cilium qui applique les NetworkPolicy
  --disable=traefik             # pas d'Ingress dans ce projet
  --disable=servicelb           # pas de LoadBalancer : on utilise kubectl port-forward
  --secrets-encryption          # Secrets Kubernetes chiffrés dans la base de k3s
)
if [[ -n "$PUBLIC_IP" ]]; then
  args+=("--tls-san=$PUBLIC_IP")  # le certificat de l'API doit contenir l'IP publique
fi

echo "Installation de k3s $K3S_VERSION..."
curl -sfL https://get.k3s.io | INSTALL_K3S_VERSION="$K3S_VERSION" sh -s - "${args[@]}"

for _ in $(seq 60); do
  [[ -s /etc/rancher/k3s/k3s.yaml ]] && break
  sleep 2
done

# Copie du kubeconfig pour l'utilisateur : adresse publique et contexte "zero-trust".
server="https://${PUBLIC_IP:-127.0.0.1}:6443"
home_dir="$(getent passwd "$KUBECONFIG_USER" | cut -d: -f6)"
target="$home_dir/zero-trust.kubeconfig"
sed -e "s#https://127.0.0.1:6443#$server#" -e 's/default$/zero-trust/' \
  /etc/rancher/k3s/k3s.yaml > "$target"
chown "$KUBECONFIG_USER:" "$target"
chmod 600 "$target"
echo "k3s installé. kubeconfig : $target (serveur $server)"
