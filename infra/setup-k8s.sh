#!/usr/bin/env bash
# =============================================================================
# infra/setup-k8s.sh
# Single-node Kubernetes setup for Ubuntu 22.04 (VMware VM)
# Run as root or with sudo.
# =============================================================================
set -euo pipefail

K8S_VERSION="1.30"
POD_CIDR="10.244.0.0/16"   # flannel default

log() { echo "[$(date '+%H:%M:%S')] $*"; }

# ── 0. Pre-flight ─────────────────────────────────────────────────────────────
log "Pre-flight checks…"
[[ "$(id -u)" -eq 0 ]] || { echo "Run as root (sudo $0)"; exit 1; }

# Disable swap (required by k8s)
swapoff -a
sed -i '/\sswap\s/s/^/#/' /etc/fstab

# ── 1. Kernel modules & sysctl ────────────────────────────────────────────────
log "Loading kernel modules…"
cat >/etc/modules-load.d/k8s.conf <<'EOF'
overlay
br_netfilter
EOF
modprobe overlay
modprobe br_netfilter

cat >/etc/sysctl.d/k8s.conf <<'EOF'
net.bridge.bridge-nf-call-iptables  = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward                 = 1
EOF
sysctl --system

# ── 2. Container runtime: containerd ─────────────────────────────────────────
log "Installing containerd…"
apt-get update -qq
apt-get install -y -qq containerd

mkdir -p /etc/containerd
containerd config default >/etc/containerd/config.toml
sed -i 's/SystemdCgroup = false/SystemdCgroup = true/' /etc/containerd/config.toml
systemctl restart containerd
systemctl enable containerd

# ── 3. kubeadm / kubelet / kubectl ────────────────────────────────────────────
log "Installing Kubernetes ${K8S_VERSION}…"
apt-get install -y -qq apt-transport-https ca-certificates curl gpg
curl -fsSL "https://pkgs.k8s.io/core:/stable:/v${K8S_VERSION}/deb/Release.key" \
  | gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
echo "deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] \
https://pkgs.k8s.io/core:/stable:/v${K8S_VERSION}/deb/ /" \
  >/etc/apt/sources.list.d/kubernetes.list
apt-get update -qq
apt-get install -y -qq kubelet kubeadm kubectl
apt-mark hold kubelet kubeadm kubectl

# ── 4. Initialize the cluster ─────────────────────────────────────────────────
log "Initializing k8s control-plane (single-node)…"
kubeadm init --pod-network-cidr="${POD_CIDR}"

# Configure kubectl for root
mkdir -p "$HOME/.kube"
cp /etc/kubernetes/admin.conf "$HOME/.kube/config"
chown "$(id -u):$(id -g)" "$HOME/.kube/config"

# Allow scheduling pods on control-plane (single-node)
kubectl taint nodes --all node-role.kubernetes.io/control-plane-

# ── 5. CNI: Flannel ───────────────────────────────────────────────────────────
log "Deploying Flannel CNI…"
kubectl apply -f https://github.com/flannel-io/flannel/releases/latest/download/kube-flannel.yml

# ── 6. Wait for node Ready ────────────────────────────────────────────────────
log "Waiting for node to become Ready…"
kubectl wait --for=condition=Ready node --all --timeout=180s

log "✅ Single-node Kubernetes is ready!"
kubectl get nodes -o wide
