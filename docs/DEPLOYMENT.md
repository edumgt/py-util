# README – VMware + K8s + Harbor + FastAPI 전체 구성 가이드

## 아키텍처 개요

```
┌─────────────────────────────────────────────────────────────────┐
│  VMware Workstation / Fusion                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Ubuntu 22.04 VM (single-node Kubernetes)                │  │
│  │                                                           │  │
│  │   ┌─────────────────┐     ┌──────────────────────────┐  │  │
│  │   │  harbor ns       │     │  netapp ns                │  │
│  │   │  Pod: registry:2 │     │  Pod: fastapi (uvicorn)  │  │  │
│  │   │  NodePort 30500  │─────▶  NodePort 30800          │  │  │
│  │   └─────────────────┘ pull └──────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
         ▲ push                              ▲ access
         │                                   │
  GitHub Actions                        http://<VM_IP>:30800/docs
  (build → push → deploy)
```

## 사전 준비

| 항목 | 내용 |
|------|------|
| Hypervisor | VMware Workstation 17+ / Fusion 13+ |
| VM OS | Ubuntu 22.04 LTS (최소 2 vCPU, 4 GB RAM, 40 GB disk) |
| 로컬 PC | Docker Desktop (이미지 빌드용) |
| Python | 3.12+ |

---

## 1) VMware VM 설정

1. VMware에서 Ubuntu 22.04 ISO로 VM 생성
   - **네트워크 어댑터**: Bridged (브리지) 또는 NAT
   - CPU ≥ 2, RAM ≥ 4 GB, Disk ≥ 40 GB
2. VM을 부팅하고 SSH를 활성화:

```bash
sudo apt-get update && sudo apt-get install -y openssh-server
```

3. VM의 IP 주소를 확인 (이후 `NODE_IP`로 사용):

```bash
ip addr show | grep 'inet ' | awk '{print $2}'
```

---

## 2) 단일 노드 Kubernetes 설치

```bash
# VM 내부에서 실행 (root 또는 sudo)
chmod +x infra/setup-k8s.sh
sudo ./infra/setup-k8s.sh
```

스크립트가 수행하는 작업:
- swap 비활성화
- containerd 런타임 설치 및 설정
- kubeadm / kubelet / kubectl 설치
- `kubeadm init` 으로 단일 노드 클러스터 초기화
- Flannel CNI 배포
- 컨트롤플레인 노드에 Pod 스케줄링 허용 (taint 제거)

---

## 3) Harbor 레지스트리 + FastAPI 앱 배포

```bash
# VM 내부에서 실행
export NODE_IP="<VM_IP>"          # 예: 192.168.100.10
chmod +x infra/deploy-k8s-apps.sh
sudo ./infra/deploy-k8s-apps.sh "${NODE_IP}"
```

스크립트가 수행하는 작업:
- `k8s/00-namespaces.yaml` – netapp / harbor 네임스페이스 생성
- `k8s/01-harbor.yaml` – Harbor(registry:2) Pod + PVC + NodePort 30500 배포
- `k8s/02-netapp.yaml` – FastAPI(uvicorn) Pod + NodePort 30800 배포
- containerd에 인시큐어 레지스트리 설정
- Docker 이미지 빌드 → Harbor에 push → 클러스터 배포

접속:
- **FastAPI Swagger UI**: `http://<NODE_IP>:30800/docs`
- **Harbor registry**: `http://<NODE_IP>:30500`

---

## 4) 로컬 개발 (venv)

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

# FastAPI 서버 실행
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
# Swagger UI: http://localhost:8000/docs
```

---

## 5) 테스트

```bash
pytest tests/ -v
```

---

## 6) GitHub Actions CI/CD

`.github/workflows/main.yml` 이 자동으로:
1. `tests/` 실행
2. Docker 이미지 빌드
3. Harbor 레지스트리(NodePort 30500)에 push
4. kubectl로 k8s 클러스터에 배포 및 롤아웃 대기

### 필요한 GitHub Secrets / Variables

| 이름 | 설명 |
|------|------|
| `HARBOR_HOST` | Harbor NodePort 주소 (예: `192.168.100.10:30500`) |
| `HARBOR_USER` | Harbor 사용자명 (기본: `admin`) |
| `HARBOR_PASSWORD` | Harbor 비밀번호 |
| `K8S_KUBECONFIG` | base64 인코딩된 kubeconfig (`base64 -w0 ~/.kube/config`) |

---

## 7) API 엔드포인트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/health` | 헬스체크 |
| GET | `/dns?host=` | DNS 조회 |
| GET | `/myip` | 서버 호스트명·IP |
| GET | `/parse-url?url=` | URL 파싱 |
| GET | `/tcp-connect?host=&port=` | TCP 포트 연결 테스트 |
| GET | `/check-ports?host=&ports=` | 멀티 포트 일괄 점검 |
| GET | `/http-get?url=` | 외부 URL HTTP GET |
| GET | `/http-get-retry?url=` | 재시도 HTTP GET |
| GET | `/async-tcp-ping?host=&ports=` | asyncio 멀티 포트 TCP 핑 |
