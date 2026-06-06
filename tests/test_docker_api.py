from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.routers.docker import get_docker_service
from app.services.docker_service import DockerServiceError, DockerUnavailableError


class FakeDockerService:
    def summary(self):
        return {
            "available": True,
            "metrics": {
                "containers_total": 2,
                "containers_running": 1,
                "containers_exited": 1,
                "images_total": 3,
                "networks_total": 2,
                "volumes_total": 1,
            },
        }

    def containers(self, status_filter: str = "all"):
        items = [
            {
                "id": "abc123",
                "name": "web",
                "image": "nginx:latest",
                "status": "running",
                "ports": [{"container": "80/tcp", "host": "0.0.0.0:8080"}],
            },
            {
                "id": "def456",
                "name": "db",
                "image": "postgres:16",
                "status": "exited",
                "ports": [],
            },
        ]
        if status_filter == "all":
            return items
        return [i for i in items if i["status"] == status_filter]

    def images(self):
        return [{"id": "img1", "tags": ["nginx:latest"], "size_mb": 50.1}]

    def networks(self):
        return [{"id": "net1", "name": "bridge", "driver": "bridge", "containers": 2}]

    def volumes(self):
        return [{"name": "vol1", "driver": "local", "mountpoint": "/var/lib/docker/volumes/vol1"}]

    def container_stats(self, container_id: str):
        if container_id == "missing":
            raise DockerServiceError(code="NOT_FOUND", message="Container not found", detail=container_id)
        return {
            "id": "abc123",
            "name": "web",
            "cpu_percent": 10.2,
            "memory_usage_mb": 123.4,
            "memory_limit_mb": 1024,
            "memory_percent": 12.0,
            "networks": {},
        }


class UnavailableDockerService:
    def _raise(self):
        raise DockerUnavailableError(
            code="DOCKER_UNAVAILABLE",
            message="Docker daemon is not reachable. Verify Docker Desktop/Engine is running.",
            detail="connect error",
        )

    def summary(self):
        return self._raise()

    def containers(self, status_filter: str = "all"):
        return self._raise()

    def images(self):
        return self._raise()

    def networks(self):
        return self._raise()

    def volumes(self):
        return self._raise()

    def container_stats(self, container_id: str):
        return self._raise()


def test_docker_summary_ok():
    app.dependency_overrides[get_docker_service] = lambda: FakeDockerService()
    client = TestClient(app)

    r = client.get("/docker/summary")
    assert r.status_code == 200
    body = r.json()
    assert body["available"] is True
    assert body["metrics"]["containers_total"] == 2

    app.dependency_overrides.clear()


def test_docker_containers_filter():
    app.dependency_overrides[get_docker_service] = lambda: FakeDockerService()
    client = TestClient(app)

    r = client.get("/docker/containers", params={"status": "running"})
    assert r.status_code == 200
    body = r.json()
    assert body["available"] is True
    assert len(body["items"]) == 1
    assert body["items"][0]["name"] == "web"

    app.dependency_overrides.clear()


def test_docker_stats_not_found():
    app.dependency_overrides[get_docker_service] = lambda: FakeDockerService()
    client = TestClient(app)

    r = client.get("/docker/containers/missing/stats")
    assert r.status_code == 404

    app.dependency_overrides.clear()


def test_docker_unavailable_fallback():
    app.dependency_overrides[get_docker_service] = lambda: UnavailableDockerService()
    client = TestClient(app)

    r = client.get("/docker/summary")
    assert r.status_code == 200
    body = r.json()
    assert body["available"] is False
    assert body["error"]["code"] == "DOCKER_UNAVAILABLE"

    app.dependency_overrides.clear()


def test_dashboard_html_served():
    client = TestClient(app)
    r = client.get("/docker/dashboard")
    assert r.status_code == 200
    assert "Docker 분석 대시보드" in r.text
