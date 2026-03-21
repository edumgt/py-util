#!/usr/bin/env bash
# =============================================================================
# infra/deploy-k8s-apps.sh
# Deploy Harbor registry + FastAPI app onto the single-node k8s cluster.
# Run from the repo root after running setup-k8s.sh.
# Usage: ./infra/deploy-k8s-apps.sh <NODE_IP>
# =============================================================================
set -euo pipefail

NODE_IP="${1:?Usage: $0 <NODE_IP>}"
HARBOR_ADDR="${NODE_IP}:30500"
IMAGE_NAME="${HARBOR_ADDR}/netapp/python-network-advanced:latest"

log() { echo "[$(date '+%H:%M:%S')] $*"; }

# ── 1. Apply namespaces ───────────────────────────────────────────────────────
log "Creating namespaces…"
kubectl apply -f k8s/00-namespaces.yaml

# ── 2. Deploy Harbor (OCI registry) ──────────────────────────────────────────
log "Deploying Harbor registry…"
kubectl apply -f k8s/01-harbor.yaml

log "Waiting for Harbor registry pod…"
kubectl rollout status deployment/harbor -n harbor --timeout=120s

# ── 3. Configure containerd to allow insecure registry ───────────────────────
log "Configuring containerd insecure registry: ${HARBOR_ADDR}…"
CONTAINERD_CONF="/etc/containerd/conf.d/insecure-harbor.toml"
mkdir -p /etc/containerd/conf.d
cat >"${CONTAINERD_CONF}" <<EOF
[plugins."io.containerd.grpc.v1.cri".registry.mirrors."${HARBOR_ADDR}"]
  endpoint = ["http://${HARBOR_ADDR}"]
[plugins."io.containerd.grpc.v1.cri".registry.configs."${HARBOR_ADDR}".tls]
  insecure_skip_verify = true
EOF
systemctl restart containerd

# ── 4. Build & push FastAPI image ────────────────────────────────────────────
log "Building Docker image: ${IMAGE_NAME}…"
docker build -t "${IMAGE_NAME}" .

log "Pushing image to Harbor: ${HARBOR_ADDR}…"
docker push "${IMAGE_NAME}"

# ── 5. Deploy FastAPI app ─────────────────────────────────────────────────────
log "Deploying FastAPI netapp…"
# Substitute NODE_IP into the manifest
sed "s|\${NODE_IP}|${NODE_IP}|g" k8s/02-netapp.yaml | kubectl apply -f -

log "Waiting for netapp pod…"
kubectl rollout status deployment/netapp -n netapp --timeout=120s

# ── 6. Summary ────────────────────────────────────────────────────────────────
log "✅ Deployment complete!"
log "   Harbor registry : http://${HARBOR_ADDR}"
log "   FastAPI service : http://${NODE_IP}:30800/docs"
kubectl get pods -A
