from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

try:
    import docker
    from docker.errors import DockerException, NotFound
except Exception:  # pragma: no cover - handled by runtime fallback
    docker = None
    DockerException = Exception
    NotFound = Exception


@dataclass
class DockerServiceError(Exception):
    code: str
    message: str
    detail: str = ""


class DockerUnavailableError(DockerServiceError):
    pass


class DockerService:
    def __init__(self, cache_ttl_seconds: float = 2.0):
        self.cache_ttl_seconds = cache_ttl_seconds
        self._client = None
        self._cache: dict[str, tuple[float, Any]] = {}

    def _cache_get(self, key: str) -> Any | None:
        item = self._cache.get(key)
        if not item:
            return None
        expires_at, value = item
        if time.time() > expires_at:
            self._cache.pop(key, None)
            return None
        return value

    def _cache_set(self, key: str, value: Any) -> Any:
        self._cache[key] = (time.time() + self.cache_ttl_seconds, value)
        return value

    def _parse_unavailable_error(self, exc: Exception) -> DockerUnavailableError:
        msg = str(exc)
        lowered = msg.lower()
        if "permission denied" in lowered:
            message = "Docker socket permission denied. Check user permissions for Docker daemon access."
        elif "no such file" in lowered or "cannot connect" in lowered or "connection aborted" in lowered:
            message = "Docker daemon is not reachable. Verify Docker Desktop/Engine is running."
        else:
            message = "Docker environment is unavailable."
        return DockerUnavailableError(code="DOCKER_UNAVAILABLE", message=message, detail=msg)

    def _get_client(self):
        if docker is None:
            raise DockerUnavailableError(
                code="DOCKER_UNAVAILABLE",
                message="Docker SDK is not installed.",
                detail="Install python package 'docker' and retry.",
            )
        if self._client is not None:
            return self._client
        try:
            self._client = docker.from_env()
            self._client.ping()
        except (DockerException, PermissionError, FileNotFoundError) as exc:
            raise self._parse_unavailable_error(exc)
        return self._client

    @staticmethod
    def _short_id(value: str | None) -> str:
        if not value:
            return ""
        return value.replace("sha256:", "")[:12]

    @staticmethod
    def _container_ports(container_attrs: dict[str, Any]) -> list[dict[str, str]]:
        ports = container_attrs.get("NetworkSettings", {}).get("Ports", {}) or {}
        result: list[dict[str, str]] = []
        for container_port, host_bindings in ports.items():
            if not host_bindings:
                result.append({"container": container_port, "host": ""})
                continue
            for binding in host_bindings:
                result.append({"container": container_port, "host": f"{binding.get('HostIp')}:{binding.get('HostPort')}"})
        return result

    @staticmethod
    def _to_mb(value: int | float | None) -> float:
        if not value:
            return 0.0
        return round(float(value) / (1024 * 1024), 2)

    def summary(self) -> dict[str, Any]:
        cached = self._cache_get("summary")
        if cached is not None:
            return cached
        client = self._get_client()
        containers = client.containers.list(all=True)
        images = client.images.list()
        networks = client.networks.list()
        volumes = (client.volumes.list() or [])

        running = sum(1 for c in containers if c.status == "running")
        exited = sum(1 for c in containers if c.status in {"exited", "dead"})

        data = {
            "available": True,
            "cache_ttl_seconds": self.cache_ttl_seconds,
            "metrics": {
                "containers_total": len(containers),
                "containers_running": running,
                "containers_exited": exited,
                "images_total": len(images),
                "networks_total": len(networks),
                "volumes_total": len(volumes),
            },
            "generated_at": int(time.time()),
        }
        return self._cache_set("summary", data)

    def containers(self, status_filter: str = "all") -> list[dict[str, Any]]:
        client = self._get_client()
        container_list = client.containers.list(all=True)
        result: list[dict[str, Any]] = []
        for container in container_list:
            attrs = container.attrs or {}
            state = attrs.get("State", {}) or {}
            item = {
                "id": self._short_id(container.id),
                "name": container.name,
                "image": (container.image.tags[0] if getattr(container.image, "tags", None) else attrs.get("Config", {}).get("Image", "")),
                "status": container.status,
                "state": state.get("Status", container.status),
                "created": attrs.get("Created", ""),
                "started_at": state.get("StartedAt", ""),
                "finished_at": state.get("FinishedAt", ""),
                "restart_count": state.get("RestartCount", 0),
                "ports": self._container_ports(attrs),
            }
            if status_filter != "all" and item["status"] != status_filter:
                continue
            result.append(item)
        return result

    def images(self) -> list[dict[str, Any]]:
        client = self._get_client()
        image_list = client.images.list()
        result: list[dict[str, Any]] = []
        for image in image_list:
            attrs = image.attrs or {}
            result.append(
                {
                    "id": self._short_id(image.id),
                    "tags": image.tags or ["<none>:<none>"],
                    "created": attrs.get("Created", ""),
                    "size_mb": self._to_mb(attrs.get("Size", 0)),
                }
            )
        return result

    def networks(self) -> list[dict[str, Any]]:
        client = self._get_client()
        network_list = client.networks.list()
        result: list[dict[str, Any]] = []
        for network in network_list:
            attrs = network.attrs or {}
            containers = (attrs.get("Containers") or {}).keys()
            result.append(
                {
                    "id": self._short_id(network.id),
                    "name": network.name,
                    "driver": attrs.get("Driver", ""),
                    "scope": attrs.get("Scope", ""),
                    "containers": len(list(containers)),
                }
            )
        return result

    def volumes(self) -> list[dict[str, Any]]:
        client = self._get_client()
        volume_list = client.volumes.list() or []
        result: list[dict[str, Any]] = []
        for volume in volume_list:
            attrs = volume.attrs or {}
            result.append(
                {
                    "name": attrs.get("Name", ""),
                    "driver": attrs.get("Driver", ""),
                    "mountpoint": attrs.get("Mountpoint", ""),
                    "scope": attrs.get("Scope", ""),
                }
            )
        return result

    def container_stats(self, container_id: str) -> dict[str, Any]:
        client = self._get_client()
        try:
            container = client.containers.get(container_id)
        except NotFound:
            raise DockerServiceError(code="NOT_FOUND", message="Container not found", detail=container_id)

        stats = container.stats(stream=False)

        cpu_stats = stats.get("cpu_stats", {})
        precpu_stats = stats.get("precpu_stats", {})
        cpu_delta = (cpu_stats.get("cpu_usage", {}).get("total_usage", 0) - precpu_stats.get("cpu_usage", {}).get("total_usage", 0))
        system_delta = cpu_stats.get("system_cpu_usage", 0) - precpu_stats.get("system_cpu_usage", 0)
        cpus = len(cpu_stats.get("cpu_usage", {}).get("percpu_usage") or []) or 1
        cpu_percent = 0.0
        if system_delta > 0 and cpu_delta > 0:
            cpu_percent = round((cpu_delta / system_delta) * cpus * 100.0, 2)

        memory = stats.get("memory_stats", {})
        mem_usage = memory.get("usage", 0)
        mem_limit = memory.get("limit", 0)

        return {
            "id": self._short_id(container.id),
            "name": container.name,
            "cpu_percent": cpu_percent,
            "memory_usage_mb": self._to_mb(mem_usage),
            "memory_limit_mb": self._to_mb(mem_limit),
            "memory_percent": round((mem_usage / mem_limit) * 100, 2) if mem_limit else 0.0,
            "networks": stats.get("networks", {}),
            "read": stats.get("read", ""),
        }
