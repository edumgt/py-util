#!/usr/bin/env bash
# .devcontainer/post-create.sh
# Runs once after the Codespaces container is created.
set -euo pipefail

echo "==> Upgrading pip and installing project dependencies…"
python -m pip install --upgrade pip
pip install -r requirements.txt

echo "==> All dependencies installed."
echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  Python Network Advanced – Codespaces 환경 준비 완료!      ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║  테스트 실행:                                              ║"
echo "║    pytest tests/ -v                                       ║"
echo "║                                                           ║"
echo "║  FastAPI 서버 실행:                                        ║"
echo "║    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload║"
echo "║  → Swagger UI: 포트 8000 자동 포워딩 후 /docs 접속          ║"
echo "╚══════════════════════════════════════════════════════════╝"
