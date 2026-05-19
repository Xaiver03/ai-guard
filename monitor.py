"""monitor.py — 系统指标采集"""

import time
from collections import deque
from dataclasses import dataclass, field, asdict
from typing import Any, Optional, List

import psutil


@dataclass
class ProcessInfo:
    pid: int
    name: str
    cmdline: str
    mem_mb: float
    cpu_percent: float
    status: str
    create_time: float


@dataclass
class Metrics:
    ts: float
    # 内存
    mem_total_gb: float
    mem_used_gb: float
    mem_percent: float
    mem_available_gb: float
    # Swap
    swap_total_gb: float
    swap_used_gb: float
    swap_percent: float
    # 磁盘
    disk_total_gb: float
    disk_used_gb: float
    disk_free_gb: float
    disk_percent: float
    # CPU
    cpu_percent: float
    # 告警等级: normal / warn / crit
    alert_level: str = "normal"

    def to_dict(self) -> dict:
        return asdict(self)


def _gb(b: float) -> float:
    return round(b / (1024 ** 3), 2)


def collect_metrics() -> Metrics:
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    disk = psutil.disk_usage("/")
    cpu = psutil.cpu_percent(interval=0)

    return Metrics(
        ts=time.time(),
        mem_total_gb=_gb(mem.total),
        mem_used_gb=_gb(mem.used),
        mem_percent=mem.percent,
        mem_available_gb=_gb(mem.available),
        swap_total_gb=_gb(swap.total),
        swap_used_gb=_gb(swap.used),
        swap_percent=swap.percent,
        disk_total_gb=_gb(disk.total),
        disk_used_gb=_gb(disk.used),
        disk_free_gb=_gb(disk.free),
        disk_percent=disk.percent,
        cpu_percent=cpu,
    )


def collect_ai_processes(watch_keywords: list) -> list:
    """扫描匹配关键字的进程"""
    result = []
    keywords_lower = [k.lower() for k in watch_keywords]

    for proc in psutil.process_iter(["pid", "name", "cmdline", "memory_info", "cpu_percent", "status", "create_time"]):
        try:
            info = proc.info
            name = (info["name"] or "").lower()
            cmdline = " ".join(info["cmdline"] or []).lower()
            haystack = f"{name} {cmdline}"

            if not any(kw in haystack for kw in keywords_lower):
                continue

            mem_bytes = info["memory_info"].rss if info["memory_info"] else 0
            result.append(ProcessInfo(
                pid=info["pid"],
                name=info["name"] or "",
                cmdline=" ".join(info["cmdline"] or [])[:200],
                mem_mb=round(mem_bytes / (1024 * 1024), 1),
                cpu_percent=info["cpu_percent"] or 0.0,
                status=info["status"] or "",
                create_time=info["create_time"] or 0,
            ))
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    result.sort(key=lambda p: p.mem_mb, reverse=True)
    return result


class MetricsHistory:
    """环形缓冲区保存历史数据"""

    def __init__(self, maxlen: int = 150):
        self._buf: deque[dict] = deque(maxlen=maxlen)

    def push(self, m: Metrics):
        self._buf.append(m.to_dict())

    def get_all(self) -> list:
        return list(self._buf)

    @property
    def latest(self) -> Optional[dict]:
        return self._buf[-1] if self._buf else None
