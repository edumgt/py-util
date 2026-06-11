"""
22) TCP 벌크 체크: cleaned_sites.txt의 URL 목록을 읽어 포트 오픈 여부 확인 후 result.txt(TSV)로 저장
    04_tcp_connect.py의 실용 확장형 — 파일 I/O + URL 파싱 + 결과 TSV 출력
    실행: python examples/22_tcp_bulk_check.py [--infile cleaned_sites.txt] [--outfile result.txt]
          (프로젝트 루트에서)
"""
from __future__ import annotations

import argparse
import socket
import time
from urllib.parse import urlparse


def tcp_connect(host: str, port: int, timeout: float) -> dict:
    t0 = time.time()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return {"ok": True, "latency_ms": int((time.time() - t0) * 1000)}
    except Exception as e:
        return {"ok": False, "latency_ms": int((time.time() - t0) * 1000), "error": str(e)}


def iter_urls(path: str, encoding: str):
    with open(path, "r", encoding=encoding) as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            yield s


def parse_host_port(url: str, default_port: int) -> tuple[str, int]:
    """
    cleaned_sites.txt에 아래 형태들이 섞여 있어도 최대한 처리:
      - https://www.naver.com
      - http://example.com
      - www.google.com   (scheme 없음)
      - https://example.com:8443/path
    """
    u = url.strip()

    # scheme 없으면 https로 간주(원하면 여기서 http로 바꿔도 됨)
    if "://" not in u:
        u = "https://" + u

    p = urlparse(u)

    # urlparse에서 hostname/port 제공
    host = p.hostname or ""
    port = p.port

    if not host:
        # 파싱 실패 시 원문에서 최대한 host만 추출(마지막 안전장치)
        host = url.split("/")[0].replace("https://", "").replace("http://", "").split(":")[0].strip()

    if port is None:
        if (p.scheme or "").lower() == "http":
            port = 80
        elif (p.scheme or "").lower() == "https":
            port = 443
        else:
            port = default_port

    return host, int(port)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--infile", default="cleaned_sites.txt")
    ap.add_argument("--outfile", default="result.txt")
    ap.add_argument("--timeout", type=float, default=1.5)
    ap.add_argument("--default-port", type=int, default=443, help="scheme 판단 불가시 사용할 기본 포트")
    ap.add_argument("--encoding", default="utf-8", help="입력 파일 인코딩(예: utf-8, cp949)")
    args = ap.parse_args()

    total = 0
    ok_cnt = 0

    with open(args.outfile, "w", encoding="utf-8", newline="\n") as out:
        out.write("url\thost\tport\tok\tlatency_ms\terror\n")

        for url in iter_urls(args.infile, args.encoding):
            total += 1
            host, port = parse_host_port(url, args.default_port)
            
            res = tcp_connect(host, port, args.timeout)

            if res.get("ok"):
                ok_cnt += 1

            out.write(
                f"{url}\t{host}\t{port}\t{res.get('ok')}\t{res.get('latency_ms')}\t{res.get('error', '')}\n"
            )

    print(f"done: {total} sites checked, ok={ok_cnt}, fail={total-ok_cnt}")
    print(f"saved: {args.outfile}")


if __name__ == "__main__":
    main()
