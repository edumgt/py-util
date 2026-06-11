#!/usr/bin/env python3
"""
DART 감사보고서 다운로드 스크립트
company.txt의 회사명으로 DART에서 감사보고서를 검색하고 /download 폴더에 저장
"""
import re
import time
from pathlib import Path
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

DOWNLOAD_DIR = Path('/home/ubuntu/py-util/download')
COMPANY_FILE = '/home/ubuntu/py-util/company.txt'
BASE_URL = 'https://dart.fss.or.kr'

# 감사보고서 관련 키워드
AUDIT_KEYWORDS = ['감사보고서']


def parse_companies() -> list[str]:
    companies = []
    seen = set()
    with open(COMPANY_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            name = line.strip()
            # 행 위치 주석 제거: (첫 번째 행), (아래쪽 행) 등
            name = re.sub(r'\s*\([첫아][^)]*행[^)]*\)', '', name)
            name = name.strip()
            if name and name not in seen:
                seen.add(name)
                companies.append(name)
    return companies


def normalize_corp_name(name: str) -> str:
    """DART 검색용 회사명 정규화: 법인 구분자·공장/지점명 제거하여 핵심명 추출"""
    name = name.strip()
    # 공장/사업장/센터/BCP 등 suffix 먼저 제거
    name = re.sub(
        r'\s*(오산공장|오산사업장|오산\s*BCP\s*센터|뷰티사업장\s*\(오산\)|뷰티사업장[^(]*)$',
        '', name,
    )
    # (주) 제거 (앞, 중간, 뒤 모두)
    name = re.sub(r'^\(주\)\s*', '', name)
    name = re.sub(r'\s*\(주\)\s*', '', name)
    # 주)  처리 (괄호 누락된 경우)
    name = re.sub(r'^주\)\s*', '', name)
    # 주식회사 제거
    name = re.sub(r'^주식회사\s*', '', name)
    name = re.sub(r'\s*주식회사$', '', name)
    return name.strip()


def already_downloaded(company_name: str) -> list[str]:
    """이미 다운로드된 파일 목록 반환"""
    pattern = re.compile(re.escape(company_name), re.IGNORECASE)
    found = []
    for f in DOWNLOAD_DIR.iterdir():
        if '감사보고서' in f.name and pattern.search(f.name):
            found.append(f.name)
    return found


def search_audit_reports(page, company_name: str) -> list[dict]:
    """회사명으로 DART 검색 후 감사보고서 목록 반환"""
    page.goto(f'{BASE_URL}/dsab007/main.do?option=corp', timeout=30000)
    page.wait_for_load_state('networkidle')

    page.fill('#headTextCrpNm', company_name)
    # 검색 날짜 범위를 5년으로 설정
    page.evaluate('''() => {
        document.getElementById("headStartDate").value = "20200101";
        document.getElementById("headEndDate").value = "20260611";
    }''')
    page.evaluate('headSearch()')
    page.wait_for_load_state('networkidle')
    page.wait_for_timeout(2000)

    soup = BeautifulSoup(page.content(), 'html.parser')

    results = []
    for row in soup.select('table tbody tr'):
        cells = row.find_all('td')
        if len(cells) < 3:
            continue
        report_type = cells[2].get_text(strip=True)
        if any(kw in report_type for kw in AUDIT_KEYWORDS):
            link = cells[2].find('a')
            if not link:
                continue
            href = link.get('href', '')
            rcp_match = re.search(r'rcpNo=(\d+)', href)
            if rcp_match:
                results.append({
                    'rcpNo': rcp_match.group(1),
                    'date': cells[4].get_text(strip=True) if len(cells) > 4 else '',
                    'title': report_type,
                    'company_display': cells[3].get_text(strip=True) if len(cells) > 3 else company_name,
                })

    return results


def get_dcm_no(page, rcp_no: str) -> str | None:
    """보고서 뷰어 페이지에서 dcmNo 추출"""
    page.goto(f'{BASE_URL}/dsaf001/main.do?rcpNo={rcp_no}', timeout=30000)
    page.wait_for_load_state('networkidle')
    page.wait_for_timeout(1000)

    soup = BeautifulSoup(page.content(), 'html.parser')
    iframe = soup.find('iframe')
    if iframe:
        src = iframe.get('src', '')
        m = re.search(r'dcmNo=(\d+)', src)
        if m:
            return m.group(1)
    return None


def download_report(context, rcp_no: str, dcm_no: str, company_name: str) -> str | None:
    """감사보고서 ZIP 파일 다운로드"""
    dl_page = context.new_page()
    try:
        dl_page.goto(
            f'{BASE_URL}/pdf/download/main.do?rcp_no={rcp_no}&dcm_no={dcm_no}',
            timeout=30000,
        )
        dl_page.wait_for_load_state('networkidle')
        dl_page.wait_for_timeout(1000)

        # 파일명 추출
        soup = BeautifulSoup(dl_page.content(), 'html.parser')
        filename = None
        for td in soup.find_all('td', class_='tL'):
            text = td.get_text(strip=True)
            if text.endswith('.zip') or text.endswith('.pdf'):
                filename = text
                break

        if not filename:
            filename = f'[{company_name}]{rcp_no}.zip'

        # 이미 존재하면 건너뜀
        save_path = DOWNLOAD_DIR / filename
        if save_path.exists():
            print(f'    이미 존재: {filename}')
            return filename

        # 다운로드 링크 클릭
        link = dl_page.query_selector('a.btnFile')
        if not link:
            return None

        with dl_page.expect_download(timeout=60000) as dl_info:
            link.click()
        dl = dl_info.value
        dl.save_as(str(save_path))
        return filename

    finally:
        dl_page.close()


def main():
    DOWNLOAD_DIR.mkdir(exist_ok=True)
    companies = parse_companies()
    print(f'총 {len(companies)}개 회사 처리 시작\n')

    summary = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()

        for company in companies:
            # 핵심 회사명으로 정규화
            search_name = normalize_corp_name(company)
            print(f'[회사] {company}  →  검색: {search_name}')

            try:
                reports = search_audit_reports(page, search_name)

                if not reports:
                    # 원본 이름으로 재시도
                    if search_name != company:
                        reports = search_audit_reports(page, company)

                if not reports:
                    msg = '감사보고서 없음'
                    print(f'  {msg}')
                    summary.append(f'[없음] {company}')
                    continue

                print(f'  감사보고서 {len(reports)}건 발견')
                downloaded = []

                for report in reports:
                    rcp_no = report['rcpNo']
                    title = report['title']
                    date = report['date']
                    disp = report['company_display']
                    print(f'  → {disp} | {title} | {date} [rcpNo={rcp_no}]')

                    dcm_no = get_dcm_no(page, rcp_no)
                    if not dcm_no:
                        print('    dcmNo 추출 실패, 건너뜀')
                        continue

                    filename = download_report(context, rcp_no, dcm_no, disp or company)
                    if filename:
                        print(f'    ✓ {filename}')
                        downloaded.append(filename)
                    else:
                        print('    ✗ 다운로드 실패')

                summary.append(f'[완료] {company}: {len(downloaded)}건')
                time.sleep(1)

            except Exception as e:
                print(f'  오류: {e}')
                summary.append(f'[오류] {company}: {e}')

        browser.close()

    print('\n' + '=' * 60)
    print('결과 요약')
    print('=' * 60)
    for line in summary:
        print(line)

    # 다운로드된 파일 목록
    print(f'\n다운로드 폴더: {DOWNLOAD_DIR}')
    files = sorted(DOWNLOAD_DIR.glob('*.zip')) + sorted(DOWNLOAD_DIR.glob('*.pdf'))
    print(f'총 {len(files)}개 파일:')
    for f in files:
        print(f'  {f.name}')


if __name__ == '__main__':
    main()
