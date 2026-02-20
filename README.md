# 네트워크 기초(소켓/HTTP) 완전 입문자용 Python 예제 

Docker 없이 **Windows 로컬 + venv**만으로 “소켓/HTTP”를 처음부터 연습하는 예제 20개입니다.  
각 예제는 **짧고**, **복사-실행**이 가능하도록 만들었습니다.

## 준비물
- Windows 10/11
- Python 3.11+ (권장 3.12)
- (권장) VS Code, Git for Windows

## 1) 설치(venv)
PowerShell에서 프로젝트 루트:

```powershell
python -m venv venv
venv\Scripts\activate
python -m pip install -U pip
pip install -r requirements.txt
```

> 대부분 예제는 표준 라이브러리만 사용합니다. `requests`는 일부 HTTP 예제에서만 씁니다.

## 2) 실행(추천 순서)
- **docs/LEARNING_PATH.md** 를 먼저 읽고, 01 → 20 순서로 실행하세요.

```powershell
python examples\01_what_is_ip_port.py --host example.com
python examples\04_tcp_connect.py --host example.com --port 443
python examples\08_http_get_urllib.py --url https://example.com
python examples\12_local_http_server.py
```

## 3) 로컬 서버 예제(터미널 2개 필요)
### A) TCP 에코 서버
터미널 1:
```powershell
python examples\15_tcp_echo_server.py
```
터미널 2:
```powershell
python examples\16_tcp_echo_client.py --msg "hello"
```

### B) 로컬 HTTP 서버 + 클라이언트
터미널 1:
```powershell
python examples\12_local_http_server.py
```
터미널 2:
```powershell
python examples\13_local_http_client.py --base http://127.0.0.1:8001
```

## 4) 한 번에 다 돌리기(가능한 것만)
```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_safe.ps1
```

## 5) Git 체크포인트(태그)
- `p0-start` : 프로젝트 시작(설치/실행)
- `p1-socket` : 소켓 기초 예제 묶음
- `p2-http` : HTTP 기초 예제 묶음
- `p3-local` : 로컬 서버/클라이언트 예제 묶음
- `p4-async` : asyncio/동시성 맛보기

