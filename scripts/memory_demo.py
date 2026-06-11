"""
시스템 메모리 조회 및 MemoryError 처리 데모
- 메모리 정보 조회: psutil / Windows ctypes / /proc/meminfo 순으로 시도
- 안전한 메모리 할당 루프(목표 GB까지만 시도) + MemoryError 처리
실행: python scripts/memory_demo.py
"""

from __future__ import annotations
import os
import gc
import time
from typing import Optional, Dict


def bytes_to_gb(n: int) -> float:
    return n / (1024 ** 3)


def get_mem_info() -> Optional[Dict[str, int]]:
    """
    가능한 경우:
    1) psutil (권장)
    2) Windows: GlobalMemoryStatusEx
    3) Linux: /proc/meminfo
    반환 키(바이트): total, available, used, free
    """
    # 1) psutil (가장 정확/간단)
    try:
        import psutil  # pip install psutil
        vm = psutil.virtual_memory()
        return {
            "total": int(vm.total),
            "available": int(vm.available),
            "used": int(vm.used),
            "free": int(getattr(vm, "free", 0)),
        }
    except Exception:
        pass

    # 2) Windows: ctypes
    if os.name == "nt":
        try:
            import ctypes

            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
            total = int(stat.ullTotalPhys)
            avail = int(stat.ullAvailPhys)
            used = total - avail
            return {"total": total, "available": avail, "used": used, "free": avail}
        except Exception:
            return None

    # 3) Linux: /proc/meminfo
    if os.path.exists("/proc/meminfo"):
        try:
            info = {}
            with open("/proc/meminfo", "r", encoding="utf-8") as f:
                for line in f:
                    k, v = line.split(":", 1)
                    info[k.strip()] = v.strip()

            # kB 단위 -> bytes
            def kb_to_bytes(s: str) -> int:
                num = int(s.split()[0])
                return num * 1024

            total = kb_to_bytes(info["MemTotal"])
            # MemAvailable이 있으면 우선 사용
            avail = kb_to_bytes(info.get("MemAvailable", info.get("MemFree", "0 kB")))
            used = total - avail
            free = kb_to_bytes(info.get("MemFree", "0 kB"))
            return {"total": total, "available": avail, "used": used, "free": free}
        except Exception:
            return None

    return None


def print_mem_info(prefix: str = "") -> None:
    mi = get_mem_info()
    if not mi:
        print(prefix + "메모리 정보를 가져오지 못했습니다. (psutil 설치 권장: pip install psutil)")
        return
    print(
        prefix
        + f"RAM total={bytes_to_gb(mi['total']):.2f}GB, "
          f"available={bytes_to_gb(mi['available']):.2f}GB, "
          f"used={bytes_to_gb(mi['used']):.2f}GB"
    )


def safe_overflow_demo(target_gb: float = 1.0, step_mb: int = 64, pause_sec: float = 0.1) -> None:
    """
    target_gb: 여기까지만 할당을 시도 (안전장치)
    step_mb: 한 번에 추가 할당하는 블록 크기
    """
    blocks = []
    allocated = 0

    step_bytes = step_mb * 1024 * 1024
    target_bytes = int(target_gb * (1024 ** 3))

    print_mem_info("[BEFORE] ")
    print(f"할당 데모 시작: 목표={target_gb}GB, step={step_mb}MB")

    try:
        while allocated < target_bytes:
            # 실제 메모리 할당(연속 메모리 필요)
            blocks.append(bytearray(step_bytes))
            allocated += step_bytes

            # 진행 출력
            print(f"allocated={bytes_to_gb(allocated):.2f}GB", end="  |  ")
            print_mem_info()

            time.sleep(pause_sec)

        print(f"\n목표치({target_gb}GB)까지 할당 완료. (강제 OOM까지는 가지 않음)")

    except MemoryError as e:
        # 여기서 MemoryError를 처리
        print("\n✅ MemoryError 발생! (메모리 부족/할당 실패)")
        print("에러 메시지:", e)
        print("대응 예시: 배치 크기 줄이기, 스트리밍 처리, 캐시 비우기, 임시 객체 해제 등")

    finally:
        # 반드시 해제(중요)
        blocks.clear()
        gc.collect()
        print_mem_info("[AFTER ] ")
        print("할당했던 메모리를 해제했습니다.")


if __name__ == "__main__":
    # 1) 메모리 정보만 보고 싶으면 아래 한 줄만 실행해도 됨
    # print_mem_info()

    # 2) overflow(메모리 부족) 예외 처리 데모
    safe_overflow_demo(target_gb=1.0, step_mb=128, pause_sec=0.05)
