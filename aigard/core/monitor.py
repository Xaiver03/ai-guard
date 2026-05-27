"""monitor.py — 系统指标采集"""

import time
import subprocess
import re
from collections import deque
from dataclasses import dataclass, field, asdict
from typing import Any, Optional, List

import psutil


@dataclass(slots=True)
class ProcessInfo:
    """进程信息"""
    pid: int
    name: str
    cmdline: str
    mem_mb: float
    cpu_percent: float
    status: str
    create_time: float


@dataclass(slots=True)
class Metrics:
    """系统指标"""
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


def _get_memory_from_vm_stat() -> tuple:
    """
    从 vm_stat 获取内存数据，使用合理的内存压力算法

    Returns:
        (used_gb, percent, available_gb, total_gb)
    """
    try:
        result = subprocess.run(['vm_stat'], capture_output=True, text=True, timeout=2)
        lines = result.stdout.strip().split('\n')

        # 提取页大小
        page_size_match = re.search(r'page size of (\d+) bytes', lines[0])
        page_size = int(page_size_match.group(1)) if page_size_match else 16384

        # 解析各项数据
        data = {}
        for line in lines[1:]:
            match = re.match(r'"?([^"]+)"?:\s+(\d+)\.?', line)
            if match:
                key = match.group(1).strip()
                value = int(match.group(2))
                data[key] = value

        # 计算内存（GB）
        def pages_to_gb(pages):
            return (pages * page_size) / (1024**3)

        active_gb = pages_to_gb(data.get('Pages active', 0))
        inactive_gb = pages_to_gb(data.get('Pages inactive', 0))
        wired_gb = pages_to_gb(data.get('Pages wired down', 0))
        free_gb = pages_to_gb(data.get('Pages free', 0))
        speculative_gb = pages_to_gb(data.get('Pages speculative', 0))
        compressed_gb = pages_to_gb(data.get('Pages stored in compressor', 0))
        compressor_gb = pages_to_gb(data.get('Pages occupied by compressor', 0))

        # Total（从 psutil 获取，更准确）
        total_gb = psutil.virtual_memory().total / (1024**3)

        # Available = Free + Inactive + Speculative
        # （Inactive 可以被快速回收，Speculative 是预读的页面）
        available_gb = free_gb + inactive_gb + speculative_gb

        # Used（物理内存实际占用）= Wired + Active + Inactive + Compressor
        # 注意：这里用 Compressor（压缩后占用的物理空间），不是 Compressed（原始大小）
        physical_used_gb = wired_gb + active_gb + inactive_gb + compressor_gb

        # Percent（内存压力）= (Total - Available) / Total
        # 这个百分比反映"还剩多少可用"，不会超过 100%
        percent = ((total_gb - available_gb) / total_gb * 100) if total_gb > 0 else 0

        return (
            round(physical_used_gb, 2),
            round(percent, 1),
            round(available_gb, 2),
            round(total_gb, 2)
        )
    except Exception as e:
        # 降级到 psutil
        return None


def collect_metrics() -> Metrics:
    # 尝试使用 vm_stat（活动监视器算法）
    vm_stat_result = _get_memory_from_vm_stat()

    if vm_stat_result:
        mem_used_gb, mem_percent, mem_available_gb, mem_total_gb = vm_stat_result
    else:
        # 降级到 psutil
        mem = psutil.virtual_memory()
        mem_total_gb = _gb(mem.total)
        mem_used_gb = _gb(mem.used)
        mem_percent = mem.percent
        mem_available_gb = _gb(mem.available)

    swap = psutil.swap_memory()
    disk = psutil.disk_usage("/")
    cpu = psutil.cpu_percent(interval=0)

    # 修复磁盘百分比：macOS APFS 中 disk.used 不包含快照/预留空间
    # 正确算法: (total - free) / total，反映用户实际可用空间占比
    disk_percent_corrected = round(((disk.total - disk.free) / disk.total) * 100, 1) if disk.total > 0 else 0.0

    return Metrics(
        ts=time.time(),
        mem_total_gb=mem_total_gb,
        mem_used_gb=mem_used_gb,
        mem_percent=mem_percent,
        mem_available_gb=mem_available_gb,
        swap_total_gb=_gb(swap.total),
        swap_used_gb=_gb(swap.used),
        swap_percent=swap.percent,
        disk_total_gb=_gb(disk.total),
        disk_used_gb=_gb(disk.total - disk.free),  # 修正：total-free 才是实际占用
        disk_free_gb=_gb(disk.free),
        disk_percent=disk_percent_corrected,
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
            cmdline_parts = info["cmdline"] or []
            cmdline = " ".join(cmdline_parts).lower()
            haystack = f"{name} {cmdline}"

            if not any(kw in haystack for kw in keywords_lower):
                continue

            mem_bytes = info["memory_info"].rss if info["memory_info"] else 0
            result.append(ProcessInfo(
                pid=info["pid"],
                name=info["name"] or "",
                cmdline=" ".join(cmdline_parts)[:120],
                mem_mb=round(mem_bytes / (1024 * 1024), 1),
                cpu_percent=info["cpu_percent"] or 0.0,
                status=info["status"] or "",
                create_time=info["create_time"] or 0,
            ))
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    result.sort(key=lambda p: p.mem_mb, reverse=True)
    return result


def collect_all_processes() -> list:
    """获取所有进程（类似活动监视器）"""
    result = []

    for proc in psutil.process_iter(["pid", "name", "cmdline", "memory_info", "cpu_percent", "status", "create_time"]):
        try:
            info = proc.info
            mem_bytes = info["memory_info"].rss if info["memory_info"] else 0
            result.append(ProcessInfo(
                pid=info["pid"],
                name=info["name"] or "",
                cmdline=" ".join(info["cmdline"] or [])[:120],
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

    def __init__(self, maxlen: int = 60):
        self._buf: deque[dict] = deque(maxlen=maxlen)

    def push(self, m: Metrics):
        self._buf.append(m.to_dict())

    def get_all(self) -> list:
        return list(self._buf)

    @property
    def latest(self) -> Optional[dict]:
        return self._buf[-1] if self._buf else None
