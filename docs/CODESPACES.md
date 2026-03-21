# GitHub Codespaces 검증 가이드

이 저장소는 **GitHub Codespaces** 에서 바로 열어 전체 기능을 검증할 수 있습니다.

---

## ❓ "Codespaces에서 VMware를 설치하고 그 위에 k8s를 올릴 수 있나?"

**결론: VMware는 불가능하지만, Kubernetes는 가능합니다.**

| 항목 | 가능 여부 | 이유 |
|------|-----------|------|
| **VMware Workstation/Fusion 설치** | ❌ 불가 | VMware는 하드웨어 하이퍼바이저(VT-x/AMD-V)가 필요하지만, Codespaces는 컨테이너 환경이라 중첩 하이퍼바이저를 지원하지 않음 |
| **단일 노드 k8s (kubeadm)** | ❌ 불가 | kubeadm은 systemd, 커널 모듈(overlay, br_netfilter) 등 전체 OS 권한이 필요 |
| **k3d (Docker 기반 경량 k8s)** | ✅ 가능 | Docker 컨테이너 안에서 k3s 클러스터를 실행 — Codespaces의 docker-in-docker 기능으로 완벽하게 작동 |
| **FastAPI 단위 테스트** | ✅ 가능 | Python 환경만 있으면 됨 |
| **FastAPI uvicorn 서버** | ✅ 가능 | Python 환경만 있으면 됨 |

### VMware가 Codespaces에서 불가능한 이유

```
[Codespaces 환경]
  Linux Container (Docker)
    └── Python, Docker daemon, k3d
         └── k3d cluster (k3s in Docker)
              └── Harbor Pod
              └── FastAPI Pod
```

VMware는 물리적 CPU의 가상화 명령어를 직접 사용해야 합니다.
컨테이너는 커널을 호스트와 공유하기 때문에 이 권한이 없습니다.

### ✅ k3d가 해결책인 이유

k3d는 k3s(경량 Kubernetes)를 **Docker 컨테이너 안에서** 실행합니다.
Codespaces의 `docker-in-docker` 기능을 사용하면 컨테이너 안에서 Docker를 실행할 수 있어,
k3d로 **완전한 Kubernetes 클러스터**를 Codespaces에서 구동할 수 있습니다.

---

## ❓ "Codespaces가 4코어 8GB를 지원하나요?"

**결론: ✅ 예, 4코어/8GB는 공식 지원되는 GitHub Codespaces 머신 크기입니다.**

### 지원되는 머신 크기 (2025년 기준)

| 머신 크기 | vCPU | RAM | 스토리지 | 무료 시간\* | 이 프로젝트 용도 |
|-----------|------|-----|----------|------------|-----------------|
| **2-core** | 2 | 4 GB | 32 GB | **60 h/월** | 테스트·uvicorn 직접 실행 |
| **4-core** | 4 | 8 GB | 32 GB | **30 h/월** | ✅ k3d k8s 최소 권장 |
| **8-core** | 8 | 16 GB | 64 GB | **15 h/월** | k3d k8s 여유 있는 실행 |
| 16-core | 16 | 32 GB | 128 GB | 7.5 h/월 | — |
| 32-core | 32 | 64 GB | 128 GB | 3.75 h/월 | — |

> \* GitHub Free 계정 기준 120 core-hours/월.  
> 계산식: `무료 시간 = 120 core-hours ÷ vCPU 수`  
> GitHub Pro는 180 core-hours/월 (4코어 기준 45 h/월).  
> 자세한 요금 정보: <https://docs.github.com/en/billing/managing-billing-for-your-products/managing-billing-for-github-codespaces/about-billing-for-github-codespaces>

### 4코어/8GB Codespace 생성 방법

1. 저장소 페이지에서 **Code** 버튼 → **Codespaces** 탭 클릭
2. **"…" (점 세 개) 메뉴** 또는 **"New with options…"** 선택
3. **Machine type** 드롭다운에서 **4-core** 선택
4. **Create codespace** 클릭

```
Code → Codespaces → New with options…
  ┌────────────────────────────────────┐
  │ Branch: main                       │
  │ Dev container: Python Network Adv  │
  │ Region: …                          │
  │ Machine type: [ 4-core · 8 GB ▼ ] │  ← 여기서 선택
  └────────────────────────────────────┘
```

> **자동 머신 선택**: 이 저장소의 `devcontainer.json` 에는
> `"hostRequirements": { "cpus": 4, "memory": "8gb" }` 가 설정되어 있습니다.
> "New with options…" 화면에서 4코어가 **자동으로 미리 선택**됩니다.
> (강제는 아니므로 다른 크기를 선택하는 것도 가능합니다.)

### 머신 크기별 k3d 동작 비교

| 머신 | k3d 클러스터 | Harbor Pod | FastAPI Pod | 여유 |
|------|-------------|-----------|------------|------|
| 2-core / 4 GB | 매우 느림, OOM 위험 | 불안정 | 불안정 | ❌ 비권장 |
| **4-core / 8 GB** | **정상 동작** | **안정** | **안정** | **✅ 권장** |
| 8-core / 16 GB | 빠름 | 안정 | 안정 | ✅ 여유 |

---

| 방법 | 용도 | 필요 시간 | 리소스 |
|------|------|-----------|--------|
| **[A] 단위 테스트 + uvicorn** | 코드/API 검증 | ~30초 | 2코어/4GB |
| **[B] k3d 전체 k8s 스택** | 컨테이너/k8s 배포 검증 | ~5분 | **4코어/8GB** |

---

## 1) Codespaces 열기

GitHub 저장소 페이지에서:

```
Code 버튼 → Codespaces 탭 → "Create codespace on <branch>"
```

또는 아래 배지를 클릭하세요 (README에서):

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/edumgt/Python_Network_Advanced)

> **k8s 검증(옵션 B)을 할 경우**: 컨테이너 생성 화면에서
> **4-core / 8 GB RAM** 이상의 머신 타입을 선택하세요.

컨테이너가 시작되면 `.devcontainer/post-create.sh` 가 자동으로 실행되어
Python 의존성과 k3d가 설치됩니다.

---

## [A] 단위 테스트 + FastAPI 직접 실행 (k8s 불필요)

### 2A) 테스트 실행

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

### 3A) FastAPI 서버 실행

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Codespaces는 포트 **8000**을 자동으로 포워딩하며, 브라우저에서:

- **Swagger UI**: `https://<codespace-name>-8000.app.github.dev/docs`
- **ReDoc**: `https://<codespace-name>-8000.app.github.dev/redoc`
- **헬스체크**: `https://<codespace-name>-8000.app.github.dev/health`

---

## [B] k3d 전체 Kubernetes 스택 검증 (VMware 대체)

이 옵션은 VMware + kubeadm 없이 Codespaces 안에서 **실제 k8s 클러스터**를 실행합니다.
Harbor 레지스트리 Pod + FastAPI Pod 가 k8s 위에서 동작하는 것을 완전히 검증합니다.

### 2B) k8s 클러스터 + 전체 스택 배포

```bash
bash infra/setup-codespaces-k8s.sh
```

스크립트가 수행하는 작업:

| 단계 | 내용 |
|------|------|
| 1 | k3d 로컬 이미지 레지스트리 생성 (localhost:5000) |
| 2 | k3d 클러스터 생성 (NodePort 30500, 30800 → Codespaces 호스트에 노출) |
| 3 | `k8s/00-namespaces.yaml` 적용 (harbor, netapp 네임스페이스) |
| 4 | `k8s/01-harbor.yaml` 배포 (registry:2 Pod) |
| 5 | FastAPI Docker 이미지 빌드 |
| 6 | k3d 레지스트리에 이미지 푸시 |
| 7 | `k8s/02-netapp.yaml` 배포 (FastAPI Pod) |
| 8 | 헬스체크 자동 실행 |

완료 후 아키텍처:

```
Codespaces (컨테이너)
  └── Docker daemon (docker-in-docker)
       ├── k3d-registry.localhost:5000  ← FastAPI 이미지 저장
       └── k3d 클러스터 (k3s)
            ├── harbor namespace
            │    └── Pod: registry:2  (NodePort 30500)
            └── netapp namespace
                 └── Pod: FastAPI/uvicorn  (NodePort 30800)
                      ↑ Codespaces가 30800 포트 포워딩
```

### 3B) 배포 후 검증

Codespaces 터미널에서:

```bash
# 헬스체크
curl http://localhost:30800/health
# → {"status":"ok"}

# DNS 조회
curl "http://localhost:30800/dns?host=example.com"

# URL 파싱
curl "http://localhost:30800/parse-url?url=https://example.com:443/path?q=1"

# TCP 포트 점검
curl "http://localhost:30800/tcp-connect?host=example.com&port=443"

# 포트 일괄 점검
curl "http://localhost:30800/check-ports?host=example.com&ports=80,443,8080"
```

Codespaces **PORTS 탭**에서 **30800** 포트의 공개 URL을 확인하면
외부에서도 브라우저로 접속할 수 있습니다:

- **Swagger UI**: `https://<codespace-name>-30800.app.github.dev/docs`

### 4B) k8s 클러스터 관리

```bash
# Pod 상태 확인
kubectl get pods -A

# 로그 확인
kubectl logs -n netapp deployment/netapp
kubectl logs -n harbor  deployment/harbor

# 서비스 확인
kubectl get svc -A

# 클러스터 삭제 (정리)
k3d cluster delete netlab
```

---

## 4) 개별 예제 스크립트 실행

```bash
python examples/01_what_is_ip_port.py --host example.com
python examples/03_parse_url.py --url https://example.com:443/path?q=1
python examples/04_tcp_connect.py --host example.com --port 443
python examples/08_http_get_urllib.py --url https://example.com
python examples/20_async_multi_connect.py --host example.com --ports 80,443
```

---

## 검증 체크리스트

### 옵션 A (빠른 검증)

| 항목 | 명령 | 기대 결과 |
|------|------|-----------|
| 의존성 설치 | `pip list \| grep fastapi` | `fastapi 0.115.x` |
| 테스트 전체 | `pytest tests/ -v` | 11 passed |
| FastAPI 서버 | `uvicorn app.main:app --port 8000` | 포트 8000 오픈 |
| Swagger UI | 브라우저에서 `/docs` | API 문서 렌더링 |
| 헬스체크 | `curl localhost:8000/health` | `{"status":"ok"}` |

### 옵션 B (전체 k8s 스택)

| 항목 | 명령 | 기대 결과 |
|------|------|-----------|
| k3d 설치 | `k3d version` | `k3d version vX.X.X` |
| kubectl 설치 | `kubectl version --client` | `Client Version: vX.X.X` |
| 전체 배포 | `bash infra/setup-codespaces-k8s.sh` | ✅ 완료 메시지 |
| k8s Pod 확인 | `kubectl get pods -A` | harbor/netapp Pod `Running` |
| FastAPI (k8s) | `curl localhost:30800/health` | `{"status":"ok"}` |
| Swagger (k8s) | 브라우저 `:30800/docs` | API 문서 렌더링 |
