#!/usr/bin/env bash
# .devcontainer/post-create.sh
# Runs once after the Codespaces container is created.
set -euo pipefail

# ── 1. Python dependencies ────────────────────────────────────────────────────
echo "==> Upgrading pip and installing project dependencies…"
python -m pip install --upgrade pip
pip install -r requirements.txt

# ── 2. k3d (k3s in Docker – lightweight Kubernetes for Codespaces) ────────────
echo "==> Installing k3d…"
curl -s https://raw.githubusercontent.com/k3d-io/k3d/main/install.sh | bash
echo "    k3d $(k3d version --short 2>/dev/null | head -1) installed."

# ── 3. Verify tools ───────────────────────────────────────────────────────────
echo "==> Tool versions:"
echo "    python  : $(python --version)"
echo "    docker  : $(docker --version 2>/dev/null || echo 'starting…')"
echo "    kubectl : $(kubectl version --client --short 2>/dev/null | head -1)"
echo "    k3d     : $(k3d version --short 2>/dev/null | head -1)"

echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║  Python Network Advanced – Codespaces 환경 준비 완료!          ║"
echo "╠═══════════════════════════════════════════════════════════════╣"
echo "║  [A] 단위 테스트 / FastAPI 직접 실행 (k8s 불필요):              ║"
echo "║    pytest tests/ -v                                           ║"
echo "║    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload   ║"
echo "║                                                               ║"
echo "║  [B] 전체 k8s 스택 검증 (k3d – VMware 불필요):                  ║"
echo "║    bash infra/setup-codespaces-k8s.sh                        ║"
echo "║    → 완료 후 http://localhost:30800/docs 접속                   ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
