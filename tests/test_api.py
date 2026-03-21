"""Tests for the FastAPI application endpoints."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_parse_url_basic():
    r = client.get("/parse-url", params={"url": "https://example.com:443/path?q=1"})
    assert r.status_code == 200
    data = r.json()
    assert data["scheme"] == "https"
    assert data["hostname"] == "example.com"
    assert data["port"] == 443
    assert data["path"] == "/path"
    assert data["query"] == "q=1"


def test_parse_url_missing_param():
    r = client.get("/parse-url")
    assert r.status_code == 422  # validation error – url is required


def test_myip():
    r = client.get("/myip")
    assert r.status_code == 200
    data = r.json()
    assert "hostname" in data
    assert "local_ip" in data


def test_dns_lookup_valid():
    r = client.get("/dns", params={"host": "localhost"})
    assert r.status_code == 200
    data = r.json()
    assert data["host"] == "localhost"
    assert "ip" in data


def test_tcp_connect_refused():
    # Port 1 is virtually always closed – we just verify the schema, not the result.
    r = client.get("/tcp-connect", params={"host": "127.0.0.1", "port": 1})
    assert r.status_code == 200
    data = r.json()
    assert "ok" in data
    assert "latency_ms" in data


def test_check_ports_bad_ports():
    r = client.get("/check-ports", params={"host": "127.0.0.1", "ports": "abc,xyz"})
    assert r.status_code == 400


def test_check_ports_schema():
    r = client.get("/check-ports", params={"host": "127.0.0.1", "ports": "1,2"})
    assert r.status_code == 200
    data = r.json()
    assert "results" in data
    assert len(data["results"]) == 2


@pytest.mark.anyio
async def test_async_tcp_ping_schema():
    r = client.get("/async-tcp-ping", params={"host": "127.0.0.1", "ports": "1,2"})
    assert r.status_code == 200
    data = r.json()
    assert "results" in data


def test_async_tcp_ping_bad_ports():
    r = client.get("/async-tcp-ping", params={"host": "127.0.0.1", "ports": "abc"})
    assert r.status_code == 400
