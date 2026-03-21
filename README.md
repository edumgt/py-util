# Python Network Advanced – FastAPI on Kubernetes (VMware)

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/edumgt/Python_Network_Advanced)

네트워크 기초(소켓/HTTP) Python 예제를 **FastAPI + uvicorn** REST API로 서빙하고,
**VMware VM** 위의 **단일 노드 Kubernetes** 클러스터에 배포하는 프로젝트입니다.
이미지는 클러스터 내 **Harbor** Pod(레지스트리)에 push/pull 하며,
**GitHub Actions**이 빌드 → push → 배포를 자동화합니다.

> **Codespaces 검증 가이드** → [docs/CODESPACES.md](docs/CODESPACES.md)  
> **전체 배포 가이드** → [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)

## Codespaces에서 바로 검증하기

로컬 설치 없이 브라우저만으로 이 저장소를 완전히 검증할 수 있습니다.

> **💡 VMware 없이 k8s 검증 가능!** — Codespaces 안에서 k3d(Docker 기반 경량 k8s)로
> Harbor 레지스트리 + FastAPI Pod를 실제 Kubernetes 위에서 구동합니다.

```
[A] 빠른 검증 (코드/API 테스트, 2코어/4GB):
    pytest tests/ -v
    uvicorn app.main:app --host 0.0.0.0 --port 8000

[B] 전체 k8s 스택 검증 (VMware 불필요, 4코어/8GB 권장):
    bash infra/setup-codespaces-k8s.sh
    → Harbor Pod + FastAPI Pod가 k8s 위에서 동작
    → http://localhost:30800/docs 에서 Swagger UI 확인
```

자세한 가이드 → [docs/CODESPACES.md](docs/CODESPACES.md)

## 아키텍처

```
GitHub Actions
  │ build & push
  ▼
Harbor registry Pod (NodePort 30500, namespace: harbor)
  │ pull
  ▼
FastAPI(uvicorn) Pod (NodePort 30800, namespace: netapp)
  ← 모두 단일 노드 k8s (VMware Ubuntu VM) 위에서 실행
```

## 빠른 시작 – 로컬 개발

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt

# FastAPI 서버 실행
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
# Swagger UI: http://localhost:8000/docs
```

## 빠른 시작 – Kubernetes 배포

```bash
# 1) VMware VM에 단일 노드 k8s 설치
sudo ./infra/setup-k8s.sh

# 2) Harbor + FastAPI 앱 배포 (NODE_IP = VM IP)
sudo ./infra/deploy-k8s-apps.sh <NODE_IP>

# 접속: http://<NODE_IP>:30800/docs
```

## 테스트

```bash
pytest tests/ -v
```

## 예제 스크립트 (직접 실행)

| 스크립트 | 설명 |
|----------|------|
| `examples/01_what_is_ip_port.py` | DNS 조회 |
| `examples/04_tcp_connect.py` | TCP 접속 테스트 |
| `examples/08_http_get_urllib.py` | urllib HTTP GET |
| `examples/20_async_multi_connect.py` | asyncio 멀티 접속 |

- 학습 순서: **docs/LEARNING_PATH.md** 참고
- Git 태그: `p0-start` `p1-socket` `p2-http` `p3-local` `p4-async`
