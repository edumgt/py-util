"""
21) URL 목록 정규화·중복 제거: sites.txt → cleaned_sites.txt
    03_parse_url.py의 실용 확장형 — 파일 I/O + scheme 자동 보완 + 중복 제거
    실행: python examples/21_normalize_url_list.py  (프로젝트 루트에서)
"""
from urllib.parse import urlparse

IN_FILE = "sites.txt"
OUT_FILE = "cleaned_sites.txt"


def normalize(line: str) -> str | None:
    line = line.strip()
    if not line or line.startswith("#"):
        return None

    # scheme 없으면 https:// 붙이기
    if "://" not in line:
        line = "https://" + line

    p = urlparse(line)
    if not p.netloc:   # 잘못된 형태는 제외
        return None

    # 호스트 소문자 정규화
    return p._replace(scheme=p.scheme.lower(), netloc=p.netloc.lower()).geturl()


def main():
    with open(IN_FILE, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()

    urls = []
    seen = set()

    for raw in lines:
        u = normalize(raw)
        if not u:
            continue
        if u in seen:
            continue
        seen.add(u)
        urls.append(u)

    with open(OUT_FILE, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(urls) + ("\n" if urls else ""))

    print(f"입력 {len(lines)}줄 → 유효 URL {len(urls)}개 저장: {OUT_FILE}")


if __name__ == "__main__":
    main()
