"""
FastAPI application – wraps the Python network utility examples as REST API endpoints.
Run locally:  uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
"""
from __future__ import annotations

import asyncio
import ipaddress
import socket
import time
from urllib.parse import urlparse

import requests as _requests
from fastapi import FastAPI, HTTPException, Query
from tenacity import retry, stop_after_attempt, wait_exponential_jitter

app = FastAPI(
    title="Python Network Advanced API",
    description="네트워크 유틸리티를 FastAPI/uvicorn 기반 REST API로 제공합니다.",
    version="1.0.0",
)

# ---------------------------------------------------------------------------
# SSRF guard – only allow public http/https targets
# ---------------------------------------------------------------------------
_ALLOWED_SCHEMES = {"http", "https"}
_PRIVATE_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
]


def _validate_external_url(url: str) -> None:
    """Raise HTTPException if *url* targets a private/internal address or uses a
    disallowed scheme, preventing Server-Side Request Forgery (SSRF)."""
    parsed = urlparse(url)
    if parsed.scheme not in _ALLOWED_SCHEMES:
        raise HTTPException(status_code=400, detail=f"URL scheme '{parsed.scheme}' is not allowed. Use http or https.")
    hostname = parsed.hostname
    if not hostname:
        raise HTTPException(status_code=400, detail="URL is missing a hostname.")
    try:
        resolved_ip = socket.gethostbyname(hostname)
        addr = ipaddress.ip_address(resolved_ip)
    except (socket.gaierror, ValueError) as exc:
        raise HTTPException(status_code=400, detail=f"Cannot resolve hostname: {exc}")
    if any(addr in net for net in _PRIVATE_NETWORKS):
        raise HTTPException(status_code=400, detail="Requests to private/internal addresses are not allowed.")


# ---------------------------------------------------------------------------
# 01 – DNS lookup
# ---------------------------------------------------------------------------
@app.get("/dns", summary="DNS 조회 (host → IP)")
def dns_lookup(host: str = Query(..., description="조회할 호스트명 (예: example.com)")):
    try:
        ip = socket.gethostbyname(host)
    except socket.gaierror as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"host": host, "ip": ip}


# ---------------------------------------------------------------------------
# 02 – My hostname / local IP
# ---------------------------------------------------------------------------
@app.get("/myip", summary="현재 컨테이너/서버의 호스트명·IP")
def my_ip():
    hostname = socket.gethostname()
    try:
        ip = socket.gethostbyname(hostname)
    except socket.gaierror:
        ip = "127.0.0.1"
    return {"hostname": hostname, "local_ip": ip}


# ---------------------------------------------------------------------------
# 03 – URL parse
# ---------------------------------------------------------------------------
@app.get("/parse-url", summary="URL 파싱")
def parse_url(url: str = Query(..., description="파싱할 URL (예: https://example.com:443/path?q=1)")):
    u = urlparse(url)
    return {
        "scheme": u.scheme,
        "hostname": u.hostname,
        "port": u.port,
        "path": u.path,
        "query": u.query,
        "fragment": u.fragment,
    }


# ---------------------------------------------------------------------------
# 04 – TCP connect (port check)
# ---------------------------------------------------------------------------
@app.get("/tcp-connect", summary="TCP 포트 연결 테스트")
def tcp_connect(
    host: str = Query(..., description="대상 호스트"),
    port: int = Query(..., ge=1, le=65535, description="대상 포트"),
    timeout: float = Query(1.5, gt=0, le=10, description="타임아웃(초)"),
):
    t0 = time.time()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return {"ok": True, "host": host, "port": port, "latency_ms": int((time.time() - t0) * 1000)}
    except Exception as exc:
        return {"ok": False, "host": host, "port": port, "latency_ms": int((time.time() - t0) * 1000), "error": str(exc)}


# ---------------------------------------------------------------------------
# 05 – Check multiple ports (allowlist scan)
# ---------------------------------------------------------------------------
@app.get("/check-ports", summary="포트 목록 일괄 점검")
def check_ports(
    host: str = Query(..., description="대상 호스트"),
    ports: str = Query("80,443,8080", description="콤마로 구분된 포트 목록"),
    timeout: float = Query(1.0, gt=0, le=10),
):
    port_list = [int(p.strip()) for p in ports.split(",") if p.strip().isdigit()]
    if not port_list:
        raise HTTPException(status_code=400, detail="유효한 포트 번호가 없습니다.")
    results = []
    for p in port_list:
        t0 = time.time()
        try:
            with socket.create_connection((host, p), timeout=timeout):
                results.append({"port": p, "open": True, "latency_ms": int((time.time() - t0) * 1000)})
        except Exception:
            results.append({"port": p, "open": False, "latency_ms": int((time.time() - t0) * 1000)})
    return {"host": host, "results": results}


# ---------------------------------------------------------------------------
# 08 – HTTP GET (status + headers sample)
# ---------------------------------------------------------------------------
@app.get("/http-get", summary="외부 URL HTTP GET (헤더·상태코드 확인)")
def http_get(
    url: str = Query(..., description="요청할 URL"),
    timeout: float = Query(4.0, gt=0, le=15),
):
    _validate_external_url(url)
    try:
        # Redirects are disabled to prevent redirect-based SSRF bypass.
        # The URL has already been validated by _validate_external_url above.
        r = _requests.get(url, timeout=timeout, allow_redirects=False)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    return {
        "status_code": r.status_code,
        "url": r.url,
        "server": r.headers.get("server", ""),
        "content_type": r.headers.get("content-type", ""),
        "body_sample": r.text[:200],
    }


# ---------------------------------------------------------------------------
# 18 – HTTP GET with retry/backoff
# ---------------------------------------------------------------------------
def _get_with_retry(url: str, timeout: float) -> int:
    @retry(stop=stop_after_attempt(4), wait=wait_exponential_jitter(initial=0.3, max=2.0), reraise=True)
    def _inner():
        r = _requests.get(url, timeout=timeout)
        return r.status_code

    return _inner()


@app.get("/http-get-retry", summary="재시도(backoff) HTTP GET")
def http_get_retry(
    url: str = Query(..., description="요청할 URL"),
    timeout: float = Query(2.0, gt=0, le=10),
):
    _validate_external_url(url)
    try:
        status = _get_with_retry(url, timeout)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    return {"url": url, "final_status_code": status}


# ---------------------------------------------------------------------------
# 20 – Async multi-port TCP ping
# ---------------------------------------------------------------------------
async def _tcp_ping(host: str, port: int, timeout: float) -> dict:
    try:
        _, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=timeout)
        writer.close()
        await writer.wait_closed()
        return {"host": host, "port": port, "ok": True}
    except Exception as exc:
        return {"host": host, "port": port, "ok": False, "error": str(exc)}


@app.get("/async-tcp-ping", summary="asyncio 기반 멀티 포트 TCP 핑")
async def async_tcp_ping(
    host: str = Query(..., description="대상 호스트"),
    ports: str = Query("80,443,8080", description="콤마로 구분된 포트 목록"),
    timeout: float = Query(1.2, gt=0, le=10),
):
    port_list = [int(p.strip()) for p in ports.split(",") if p.strip().isdigit()]
    if not port_list:
        raise HTTPException(status_code=400, detail="유효한 포트 번호가 없습니다.")
    tasks = [_tcp_ping(host, p, timeout) for p in port_list]
    results = await asyncio.gather(*tasks)
    return {"host": host, "results": list(results)}


# ---------------------------------------------------------------------------
# Health-check
# ---------------------------------------------------------------------------
@app.get("/health", summary="헬스체크")
def health():
    return {"status": "ok"}
