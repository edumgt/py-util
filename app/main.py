"""
FastAPI application – network utility APIs and local Docker environment dashboard.
Run locally: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from app.routers.docker import router as docker_router
from app.routers.network import router as network_router

app = FastAPI(
    title="Python Network Advanced API",
    description="네트워크 유틸리티 + 로컬 Docker 환경 분석 대시보드를 제공합니다.",
    version="2.0.0",
)

app.include_router(network_router)
app.include_router(docker_router)


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docker/dashboard")
