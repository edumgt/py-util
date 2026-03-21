#!/usr/bin/env bash
# =============================================================================
# infra/setup-codespaces-k8s.sh
#
# Sets up a k3d (k3s-in-Docker) cluster inside Codespaces and deploys the
# full stack: Harbor registry Pod + FastAPI app Pod.
# Replaces infra/setup-k8s.sh + infra/deploy-k8s-apps.sh for cloud-based
# validation without VMware.
#
# Prerequisites (installed automatically by the devcontainer):
#   - docker  (docker-in-docker feature)
#   - kubectl (kubectl-helm-minikube feature)
#   - k3d     (post-create.sh)
#
# Run from the repository root:
#   bash infra/setup-codespaces-k8s.sh
#
# Recommended Codespaces machine: 4-core / 8 GB RAM or larger
# =============================================================================
set -euo pipefail

CLUSTER_NAME="netlab"
REGISTRY_NAME="registry.localhost"
REGISTRY_PORT="5000"
# Address used by pods inside the k3d cluster to pull from the local registry
K3D_REGISTRY="k3d-${REGISTRY_NAME}:${REGISTRY_PORT}"
IMAGE_TAG="localhost:${REGISTRY_PORT}/netapp/python-network-advanced:latest"

log() { echo "[$(date '+%H:%M:%S')] $*"; }

# ── 0. Pre-flight ─────────────────────────────────────────────────────────────
log "Pre-flight checks…"
for cmd in docker kubectl k3d; do
    command -v "$cmd" &>/dev/null \
        || { echo "ERROR: '$cmd' not found. Ensure the devcontainer post-create has completed."; exit 1; }
done

# Wait up to 30 s for the Docker daemon to become available
for i in $(seq 1 30); do
    docker info &>/dev/null && break
    echo "  Waiting for Docker daemon… (${i}/30)"
    sleep 1
done
docker info &>/dev/null || { echo "ERROR: Docker daemon is not accessible."; exit 1; }

# ── 1. k3d local registry ─────────────────────────────────────────────────────
log "Creating k3d local registry (port ${REGISTRY_PORT})…"
if k3d registry list 2>/dev/null | grep -q "${REGISTRY_NAME}"; then
    log "  Registry already exists, skipping."
else
    k3d registry create "${REGISTRY_NAME}" --port "${REGISTRY_PORT}"
    log "  Registry created: ${K3D_REGISTRY}"
fi

# ── 2. k3d cluster ────────────────────────────────────────────────────────────
log "Creating k3d cluster '${CLUSTER_NAME}'…"
if k3d cluster list 2>/dev/null | grep -q "${CLUSTER_NAME}"; then
    log "  Cluster already exists, starting it."
    k3d cluster start "${CLUSTER_NAME}" 2>/dev/null || true
else
    # Map NodePorts 30500 (Harbor) and 30800 (FastAPI) to the Codespaces host
    k3d cluster create "${CLUSTER_NAME}" \
        --registry-use "${K3D_REGISTRY}" \
        -p "30500:30500@server:0" \
        -p "30800:30800@server:0" \
        --wait
    log "  Cluster created."
fi

# ── 3. kubectl context ────────────────────────────────────────────────────────
log "Setting kubectl context to k3d-${CLUSTER_NAME}…"
kubectl config use-context "k3d-${CLUSTER_NAME}"

# ── 4. Namespaces ─────────────────────────────────────────────────────────────
log "Applying namespaces…"
kubectl apply -f k8s/00-namespaces.yaml

# ── 5. Harbor registry Pod ────────────────────────────────────────────────────
log "Deploying Harbor registry Pod (registry:2)…"
kubectl apply -f k8s/01-harbor.yaml
log "Waiting for Harbor rollout (up to 120s)…"
kubectl rollout status deployment/harbor -n harbor --timeout=120s

# ── 6. Build FastAPI Docker image ─────────────────────────────────────────────
log "Building FastAPI Docker image: ${IMAGE_TAG}…"
docker build -t "${IMAGE_TAG}" .

# ── 7. Push image to k3d registry ────────────────────────────────────────────
log "Pushing image to k3d registry (localhost:${REGISTRY_PORT})…"
docker push "${IMAGE_TAG}"

# ── 8. Deploy FastAPI app ─────────────────────────────────────────────────────
log "Deploying FastAPI netapp…"
# Substitute ${NODE_IP}:30500 in 02-netapp.yaml with the k3d registry address
# (pods inside k3d reach the local registry via k3d-<name>:<port>)
sed "s|\${NODE_IP}:30500|${K3D_REGISTRY}|g" k8s/02-netapp.yaml \
    | kubectl apply -f -
log "Waiting for netapp rollout (up to 180s)…"
kubectl rollout status deployment/netapp -n netapp --timeout=180s

# ── 9. Pod status ─────────────────────────────────────────────────────────────
log "Deployed pods:"
kubectl get pods -A

# ── 10. Health check ──────────────────────────────────────────────────────────
log "FastAPI health check (http://localhost:30800/health)…"
for i in $(seq 1 20); do
    if curl -sf http://localhost:30800/health >/dev/null 2>&1; then
        log "  Health check OK"
        break
    fi
    echo "  Waiting… (${i}/20)"
    sleep 3
done
curl -s http://localhost:30800/health && echo ""

# ── 11. Summary ───────────────────────────────────────────────────────────────
log "Codespaces k8s deployment complete!"
echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║  접속 URL (Codespaces PORTS 탭에서 포워딩 URL 확인)            ║"
echo "╠═══════════════════════════════════════════════════════════════╣"
echo "║  FastAPI Swagger UI : http://localhost:30800/docs             ║"
echo "║  FastAPI 헬스체크   : http://localhost:30800/health           ║"
echo "║  Harbor 레지스트리  : http://localhost:30500                  ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""
echo "  curl http://localhost:30800/health"
echo "  curl 'http://localhost:30800/dns?host=example.com'"
echo "  curl 'http://localhost:30800/parse-url?url=https://example.com'"
