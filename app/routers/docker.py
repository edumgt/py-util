from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse

from app.services.docker_service import DockerService, DockerServiceError, DockerUnavailableError

router = APIRouter(prefix="/docker", tags=["docker"])
_service = DockerService()


def get_docker_service() -> DockerService:
    return _service


def _fallback_payload(exc: DockerUnavailableError) -> dict:
    return {
        "available": False,
        "error": {
            "code": exc.code,
            "message": exc.message,
            "detail": exc.detail,
        },
    }


@router.get("/summary", summary="Docker 환경 요약 지표")
def docker_summary(service: DockerService = Depends(get_docker_service)):
    try:
        return service.summary()
    except DockerUnavailableError as exc:
        return _fallback_payload(exc)


@router.get("/containers", summary="Docker 컨테이너 목록")
def docker_containers(
    status: str = Query("all", description="all/running/exited 등 Docker 상태 필터"),
    service: DockerService = Depends(get_docker_service),
):
    try:
        return {"available": True, "items": service.containers(status_filter=status)}
    except DockerUnavailableError as exc:
        return _fallback_payload(exc)


@router.get("/images", summary="Docker 이미지 목록")
def docker_images(service: DockerService = Depends(get_docker_service)):
    try:
        return {"available": True, "items": service.images()}
    except DockerUnavailableError as exc:
        return _fallback_payload(exc)


@router.get("/networks", summary="Docker 네트워크 목록")
def docker_networks(service: DockerService = Depends(get_docker_service)):
    try:
        return {"available": True, "items": service.networks()}
    except DockerUnavailableError as exc:
        return _fallback_payload(exc)


@router.get("/volumes", summary="Docker 볼륨 목록")
def docker_volumes(service: DockerService = Depends(get_docker_service)):
    try:
        return {"available": True, "items": service.volumes()}
    except DockerUnavailableError as exc:
        return _fallback_payload(exc)


@router.get("/containers/{container_id}/stats", summary="컨테이너 리소스 통계")
def docker_container_stats(container_id: str, service: DockerService = Depends(get_docker_service)):
    try:
        return {"available": True, "stats": service.container_stats(container_id)}
    except DockerUnavailableError as exc:
        return _fallback_payload(exc)
    except DockerServiceError as exc:
        if exc.code == "NOT_FOUND":
            raise HTTPException(status_code=404, detail=exc.message)
        raise HTTPException(status_code=400, detail=exc.message)


@router.get("/dashboard-data", summary="대시보드용 Docker 종합 데이터")
def docker_dashboard_data(service: DockerService = Depends(get_docker_service)):
    try:
        summary = service.summary()
        return {
            "available": True,
            "summary": summary,
            "containers": service.containers(),
            "images": service.images(),
            "networks": service.networks(),
            "volumes": service.volumes(),
        }
    except DockerUnavailableError as exc:
        return _fallback_payload(exc)


@router.get("/dashboard", response_class=HTMLResponse, summary="Docker 현황 대시보드")
def docker_dashboard() -> HTMLResponse:
    dashboard_path = Path(__file__).resolve().parents[1] / "dashboard.html"
    return HTMLResponse(dashboard_path.read_text(encoding="utf-8"))
