# GitHub Codespaces 검증 가이드

이 저장소는 **GitHub Codespaces** 에서 바로 열어 전체 기능을 검증할 수 있습니다.  
VMware / 로컬 k8s / Docker 없이도 FastAPI 앱 실행 및 테스트가 가능합니다.

---

## 1) Codespaces 열기

GitHub 저장소 페이지에서:

```
Code 버튼 → Codespaces 탭 → "Create codespace on <branch>"
```

또는 아래 배지를 클릭하세요 (README에서):

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/edumgt/Python_Network_Advanced)

컨테이너가 시작되면 `.devcontainer/post-create.sh` 가 자동으로 실행되어 의존성이 설치됩니다.

---

## 2) 테스트 실행

Codespaces 터미널에서:

```bash
pytest tests/ -v
```

기대 결과:

```
tests/test_api.py::test_health                    PASSED
tests/test_api.py::test_parse_url_basic           PASSED
tests/test_api.py::test_parse_url_missing_param   PASSED
tests/test_api.py::test_myip                      PASSED
tests/test_api.py::test_dns_lookup_valid          PASSED
tests/test_api.py::test_tcp_connect_refused       PASSED
tests/test_api.py::test_check_ports_bad_ports     PASSED
tests/test_api.py::test_check_ports_schema        PASSED
tests/test_api.py::test_async_tcp_ping_schema     PASSED
tests/test_api.py::test_async_tcp_ping_bad_ports  PASSED
tests/test_parse_url.py::test_urlparse_basic      PASSED
11 passed
```

---

## 3) FastAPI 서버 실행

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Codespaces는 포트 **8000**을 자동으로 포워딩하며, 브라우저에서:

- **Swagger UI**: `https://<codespace-name>-8000.app.github.dev/docs`
- **ReDoc**: `https://<codespace-name>-8000.app.github.dev/redoc`
- **헬스체크**: `https://<codespace-name>-8000.app.github.dev/health`

---

## 4) 개별 예제 스크립트 실행

```bash
# DNS 조회
python examples/01_what_is_ip_port.py --host example.com

# URL 파싱
python examples/03_parse_url.py --url https://example.com:443/path?q=1

# TCP 포트 연결 테스트
python examples/04_tcp_connect.py --host example.com --port 443

# HTTP GET
python examples/08_http_get_urllib.py --url https://example.com

# asyncio 멀티 접속
python examples/20_async_multi_connect.py --host example.com --ports 80,443
```

---

## 5) API 엔드포인트 직접 호출 (curl / 터미널)

서버가 실행 중일 때 다른 터미널에서:

```bash
# 헬스체크
curl http://localhost:8000/health

# DNS 조회
curl "http://localhost:8000/dns?host=example.com"

# URL 파싱
curl "http://localhost:8000/parse-url?url=https://example.com:443/path?q=1"

# TCP 포트 연결 테스트
curl "http://localhost:8000/tcp-connect?host=example.com&port=443"

# 포트 일괄 점검
curl "http://localhost:8000/check-ports?host=example.com&ports=80,443,8080"

# asyncio 멀티 포트 핑
curl "http://localhost:8000/async-tcp-ping?host=example.com&ports=80,443"
```

---

## 6) VS Code 테스트 탐색기 사용

Codespaces는 VS Code Web을 제공합니다.

1. 왼쪽 사이드바 → **테스트(⚗️) 아이콘** 클릭
2. `tests/test_api.py` 에서 각 테스트 옆 ▶ 버튼으로 실행

---

## 검증 체크리스트

| 항목 | 명령 | 기대 결과 |
|------|------|-----------|
| 의존성 설치 | `pip list \| grep fastapi` | `fastapi 0.115.x` |
| 테스트 전체 | `pytest tests/ -v` | 11 passed |
| FastAPI 서버 | `uvicorn app.main:app --port 8000` | 포트 8000 오픈 |
| Swagger UI | 브라우저에서 `/docs` | API 문서 렌더링 |
| 헬스체크 | `curl localhost:8000/health` | `{"status":"ok"}` |
