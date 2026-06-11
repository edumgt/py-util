## 기업 정보 수집 – 크롤링 기술 가이드

`scripts/dart_download.py` 스크립트를 포함하여 DART·KOSIS·통계청·홈택스에서
기업 관련 데이터를 수집하는 기술적 방법을 정리합니다.

---

### 1. DART (금융감독원 전자공시시스템) – `dart.fss.or.kr`

감사보고서, 사업보고서 등 공시 서류를 자동으로 검색·다운로드합니다.

#### 핵심 엔드포인트

| 역할 | 메서드 | URL |
|------|--------|-----|
| 검색 페이지 초기화 | GET | `https://dart.fss.or.kr/dsab007/main.do?option=corp` |
| 회사명 자동완성 | GET | `https://dart.fss.or.kr/auto/autoCompleteCrp.ax?keyword={회사명}` |
| 공시 검색 (Form 제출) | POST/JS | `headSearchForm` → `headSearch()` 호출 |
| 보고서 뷰어 | GET | `https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcpNo}` |
| 파일 다운로드 팝업 | GET | `https://dart.fss.or.kr/pdf/download/main.do?rcp_no={rcpNo}&dcm_no={dcmNo}` |
| ZIP 직접 다운로드 | GET | `https://dart.fss.or.kr/pdf/download/zip.do?rcp_no={rcpNo}&dcm_no={dcmNo}` |

#### 검색 흐름

```
1. Playwright로 메인 페이지 로드 (세션/쿠키 초기화)
2. #headTextCrpNm 입력 → headSearch() 호출
3. 검색 결과 HTML 파싱 → <a href="/dsaf001/main.do?rcpNo=XXXX"> 추출
4. 보고서 뷰어 페이지 로드 → <iframe src="...dcmNo=YYYY..."> 에서 dcmNo 추출
5. 다운로드 팝업 → a.btnFile 클릭 → Playwright expect_download()
```

#### 주요 Form 파라미터 (`searchForm`)

| 파라미터 | 예시값 | 설명 |
|----------|--------|------|
| `option` | `corp` | 검색 유형 (corp=회사명) |
| `textCrpNm` | `아로마티카` | 회사명 |
| `startDate` | `20200101` | 검색 시작일 |
| `endDate` | `20260611` | 검색 종료일 |
| `publicType` | `F001`, `F002` | 보고서 유형 (F001=감사보고서, F002=연결감사) |
| `sort` | `date` | 정렬 기준 |
| `series` | `desc` | 정렬 방향 |

#### 보고서 유형 코드 (`publicType`)

| 코드 | 보고서 유형 |
|------|------------|
| `A001` | 사업보고서 |
| `A002` | 반기보고서 |
| `F001` | 감사보고서 |
| `F002` | 연결감사보고서 |
| `F003`~`F005` | 기타 감사 보고서 |

#### 실행 예시

```bash
# company.txt의 모든 회사 감사보고서 다운로드
python scripts/dart_download.py

# 다운로드 폴더의 ZIP 일괄 압축 해제
python -c "
import zipfile, pathlib
for f in pathlib.Path('download').glob('*.zip'):
    zipfile.ZipFile(f).extractall('download')
"
```

#### 주의사항

- `headSearch()` 는 JavaScript 함수로, Playwright 없이 단순 HTTP 요청으로는 검색 결과를 얻기 어렵습니다.
- DART는 별도 Open API(`opendart.fss.or.kr`)를 제공하며 API 키 발급 시 JSON으로 공시 목록 조회 가능합니다.
- 서버 부하 방지를 위해 회사당 `time.sleep(1)` 이상 간격을 유지합니다.

---

### 2. KOSIS (국가통계포털) – `kosis.kr`

업종별·지역별 집계 통계 데이터를 검색하고 통계표 ID를 확인합니다.

> KOSIS는 **개별 기업 데이터를 제공하지 않습니다.** 업종(KSIC)·지역 단위 집계 통계만 공표됩니다.

#### 주요 접근 경로

```
국내통계 → 주제별 통계 → 광업·제조업·에너지 → 광업제조업조사
국내통계 → 주제별 통계 → 보건 → 화장품산업현황  (식품의약품안전처)
국내통계 → 기관별 통계 → 국가데이터처 → 전국사업체조사
```

#### 통계표 직접 접근 URL 패턴

```
https://kosis.kr/start.jsp?orgId={orgId}&tblId={tblId}&vw_cd=MT_ZTITLE&conn_path=MT_ZTITLE
```

> 통계표 열람은 KOSIS 로그인(무료 회원가입) 후 가능합니다.

#### 주요 통계표 ID

| 통계표 | 기관 | orgId | tblId |
|--------|------|-------|-------|
| 화장품 제조업체·책임판매업체 현황 | 식약처 | `145` | `DT_145011_A001` |
| 국내 화장품산업 현황 (생산액·업체수) | 식약처 | `145` | `DT_145011_A009` |
| 생산액 상위 10개 화장품 책임판매업체 | 식약처 | `145` | `DT_145011_A005` |
| 화장품 수출입 현황 | 식약처 | `145` | `DT_145011_A006` |
| 경기도 산업별 사업체수·종사자수·매출액 | 국가데이터처 | `101` | `DT_1BD4002N` |
| 시도/산업분류별 광업제조업 주요지표 | 국가데이터처 | `101` | `DT_1FJY1104` |
| 오산시 제조업 사업체수 (e-지방지표) | 국가데이터처 | `101` | `DT_1YL5702` |
| 행정구역/산업별 고용 (사업체노동력조사) | 고용노동부 | `118` | `DT_118N_MONA49` |
| 시군구별 산업별 사업체수·종사자수 | 고용노동부 | `118` | `DT_118N_SAUPM78` |

#### KOSIS Open API 사용법 (API 키 필요)

```python
import requests

API_KEY = "발급받은_키"  # https://kosis.kr/openapi/apiUsageGuide.es
BASE = "https://kosis.kr/openapi/statisticsData.do"

params = {
    "method": "getList",
    "apiKey": API_KEY,
    "orgId": "145",
    "tblId": "DT_145011_A001",
    "itmId": "T10",        # 항목 ID (전체: ALL)
    "objL1": "ALL",        # 분류1 항목
    "prdSe": "Y",          # 수록주기 (Y=연간)
    "startPrdDe": "2020",
    "endPrdDe": "2024",
    "format": "json",
    "jsonVD": "Y",
}

resp = requests.get(BASE, params=params)
data = resp.json()
```

#### Playwright 기반 검색 결과 스크래핑

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    # 검색 실행
    page.goto("https://kosis.kr/index/index.do", wait_until="domcontentloaded")
    page.wait_for_timeout(2000)
    page.fill("#seSearchQuery", "화장품 제조업체")
    page.click("#autoSearchQuery")
    page.wait_for_timeout(7000)   # ARK 검색엔진 렌더링 대기

    # 통계표 목록 텍스트 추출
    text = page.evaluate("document.body.innerText")
    # '통계표 : N건' 이후 줄부터 파싱
```

> KOSIS 검색은 ARK 검색엔진(JavaScript 렌더링)을 사용하므로
> 단순 HTTP 요청으로는 결과를 파싱할 수 없습니다.

#### 마이크로데이터 (개별 사업체 원시데이터)

연구 목적으로 개별 사업체 수준의 원시데이터가 필요한 경우:

```
MDIS(마이크로데이터 통합서비스): https://mdis.kostat.go.kr
- 전국사업체조사, 광업제조업조사 등 원시데이터 신청 가능
- 승인 후 암호화된 파일로 제공 (통계 연구 목적 한정)
```

---

### 3. 통계청 (kostat.go.kr) – 보도자료 및 보고서 수집

통계청이 주기적으로 발표하는 조사 결과 보도자료(PDF/HWP)를 자동 수집합니다.

#### 보도자료 검색 경로

```
https://kostat.go.kr → 새소식 → 보도자료 → 검색어: "광업제조업조사"
```

#### 보도자료 목록 API

```python
import requests
from bs4 import BeautifulSoup

BASE = "https://kostat.go.kr"
LIST_URL = f"{BASE}/board/search/bbs/771/notice.do"

params = {
    "bbs_nm": "notice",
    "bbs_id": "771",
    "pageNo": "1",
    "searchType": "subject",
    "searchKey": "광업제조업조사",
}

resp = requests.get(LIST_URL, params=params,
                    headers={"User-Agent": "Mozilla/5.0"})
soup = BeautifulSoup(resp.text, "html.parser")

for item in soup.select("table.bbs_list tbody tr"):
    title_el = item.select_one("td.subject a")
    date_el = item.select_one("td.date")
    if title_el:
        print(title_el.text.strip(), "|", date_el.text.strip() if date_el else "")
        print("  URL:", BASE + title_el["href"])
```

#### 첨부파일(PDF/HWP) 다운로드

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(accept_downloads=True)
    page = context.new_page()

    page.goto("보도자료_URL")
    page.wait_for_load_state("networkidle")

    # 첨부파일 링크 탐색
    for link in page.query_selector_all("a[href*='.pdf'], a[href*='.hwp'], a[href*='download']"):
        filename = link.inner_text().strip()
        with page.expect_download() as dl_info:
            link.click()
        download = dl_info.value
        download.save_as(f"download/{download.suggested_filename or filename}")
```

#### 주요 검색 키워드

| 키워드 | 내용 |
|--------|------|
| `광업제조업조사` | 제조업 사업체 출하액·종사자·부가가치 연간 집계 |
| `전국사업체조사` | 전 산업 사업체수·종사자수 지역별 집계 |
| `기업활동조사` | 50인 이상 기업 경영지표 |
| `서비스업조사` | 서비스업 매출액·종사자 규모별 집계 |

---

### 4. 홈택스 (hometax.go.kr) – 사업자 정보 조회

사업자등록번호 기반으로 사업자 상태(과세/면세/폐업)를 조회합니다.

#### 사업자 상태 조회 API (공개 API)

국세청은 사업자등록 상태 조회 API를 공공데이터포털을 통해 제공합니다.

```python
import requests

# 국세청 사업자등록 상태조회 (data.go.kr 기반 공개 API)
API_KEY = "공공데이터포털_발급키"
URL = "https://api.odcloud.kr/api/nts-businessman/v1/status"

# 사업자번호 목록 (하이픈 제거)
biz_nos = ["1234567890", "9876543210"]

resp = requests.post(
    URL,
    params={"serviceKey": API_KEY},
    json={"b_no": biz_nos},
    headers={"Content-Type": "application/json"},
)
print(resp.json())
# 응답: {"status_code": "OK", "data": [{"b_no": "...", "b_stt": "계속사업자", ...}]}
```

| 응답 필드 | 설명 |
|-----------|------|
| `b_no` | 사업자등록번호 |
| `b_stt` | 사업자 상태 (계속사업자/휴업자/폐업자) |
| `b_stt_cd` | 상태 코드 (01=계속, 02=휴업, 03=폐업) |
| `tax_type` | 과세 유형 (부가가치세 일반/간이/면세) |
| `end_dt` | 폐업일 (폐업 시) |

#### 홈택스 웹 기반 조회 (Playwright)

사업자등록번호 없이 회사명으로 조회하는 공개 API는 존재하지 않습니다.
홈택스 웹을 통한 조회는 로그인(공동인증서·간편인증) 필요합니다.

```python
# 로그인 없이 가능한 범위: 사업자 상태 조회만 가능 (위 API 활용 권장)
# 법인 정보 상세 조회 → 법원 법인등기 열람 서비스 참고:
#   https://www.iros.go.kr  (인터넷 등기소)
```

#### 관련 공개 데이터 소스

| 소스 | 제공 정보 | URL |
|------|----------|-----|
| 공공데이터포털 | 사업자 상태 조회 API | https://www.data.go.kr |
| 인터넷 등기소 | 법인등기부 열람 (법인명 검색) | https://www.iros.go.kr |
| DART Open API | 상장·공시 법인 재무정보 | https://opendart.fss.or.kr |
| 기업마당 | 중소기업 지원 사업, 기업 정보 | https://www.bizinfo.go.kr |

---

### 요약 – 수집 가능 데이터 비교

| 사이트 | 개별 기업 조회 | 재무 데이터 | 업종 통계 | 로그인 필요 | API 제공 |
|--------|:---:|:---:|:---:|:---:|:---:|
| DART (dart.fss.or.kr) | ✅ 공시 기업만 | ✅ 감사보고서 | ✗ | ✗ | ✅ opendart |
| KOSIS (kosis.kr) | ✗ | ✗ | ✅ 업종·지역 집계 | △ 일부 | ✅ 키 필요 |
| 통계청 (kostat.go.kr) | ✗ | ✗ | ✅ 보도자료/PDF | ✗ | ✗ |
| 홈택스 (hometax.go.kr) | ✅ 사업자번호 필요 | ✗ | ✗ | △ 일부 | ✅ data.go.kr |

---

## 예제 스크립트 (직접 실행)

| 스크립트 | 설명 |
|----------|------|
| `examples/01_what_is_ip_port.py` | DNS 조회 |
| `examples/04_tcp_connect.py` | TCP 접속 테스트 |
| `examples/08_http_get_urllib.py` | urllib HTTP GET |
| `examples/20_async_multi_connect.py` | asyncio 멀티 접속 |
| `examples/21_normalize_url_list.py` | URL 목록 정규화·중복 제거 (sites.txt → cleaned_sites.txt) |
| `examples/22_tcp_bulk_check.py` | TCP 벌크 체크 — cleaned_sites.txt → result.txt (TSV) |
| `scripts/memory_demo.py` | 시스템 메모리 조회 및 MemoryError 처리 데모 |

- 학습 순서: **docs/LEARNING_PATH.md** 참고
- Git 태그: `p0-start` `p1-socket` `p2-http` `p3-local` `p4-async`
