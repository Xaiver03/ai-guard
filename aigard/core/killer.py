"""killer.py — 安全进程干预(SIGSTOP → 确认 → SIGTERM)"""

import signal
import os
from typing import Optional
import psutil
from dataclasses import dataclass


@dataclass(slots=True)
class ActionResult:
    success: bool
    message: str
    mem_freed_mb: float = 0.0


def _get_proc(pid: int) -> Optional[psutil.Process]:
    try:
        return psutil.Process(pid)
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return None


def pause_process(pid: int) -> ActionResult:
    """SIGSTOP 暂停进程,保留状态可恢复"""
    proc = _get_proc(pid)
    if not proc:
        return ActionResult(False, f"进程 {pid} 不存在")
    try:
        mem_before = proc.memory_info().rss / (1024 * 1024)
        os.kill(pid, signal.SIGSTOP)
        return ActionResult(True, f"已暂停进程 {proc.name()} (PID {pid})", round(mem_before, 1))
    except PermissionError:
        return ActionResult(False, f"权限不足,无法暂停 PID {pid}(可能需要 sudo)")
    except Exception as e:
        return ActionResult(False, str(e))


def resume_process(pid: int) -> ActionResult:
    """SIGCONT 恢复被暂停的进程"""
    proc = _get_proc(pid)
    if not proc:
        return ActionResult(False, f"进程 {pid} 不存在")
    try:
        os.kill(pid, signal.SIGCONT)
        return ActionResult(True, f"已恢复进程 {proc.name()} (PID {pid})")
    except PermissionError:
        return ActionResult(False, f"权限不足,无法恢复 PID {pid}")
    except Exception as e:
        return ActionResult(False, str(e))


def kill_process(pid: int) -> ActionResult:
    """SIGTERM 优雅终止进程(先恢复再终止,避免 STOP 状态下无法处理信号)"""
    # 自我保护:禁止终止当前进程或父进程
    current_pid = os.getpid()
    parent_pid = os.getppid()
    if pid == current_pid:
        return ActionResult(False, f"拒绝终止:PID {pid} 是 AI Guard 自身进程")
    if pid == parent_pid:
        return ActionResult(False, f"拒绝终止:PID {pid} 是 AI Guard 父进程")

    proc = _get_proc(pid)
    if not proc:
        return ActionResult(False, f"进程 {pid} 不存在")
    try:
        name = proc.name()
        mem_mb = proc.memory_info().rss / (1024 * 1024)
        # 若进程处于 stopped 状态,先 SIGCONT 再 SIGTERM
        status = proc.status()
        if status == psutil.STATUS_STOPPED:
            os.kill(pid, signal.SIGCONT)
        proc.terminate()  # SIGTERM
        return ActionResult(True, f"已终止进程 {name} (PID {pid})", round(mem_mb, 1))
    except PermissionError:
        return ActionResult(False, f"权限不足,无法终止 PID {pid}")
    except Exception as e:
        return ActionResult(False, str(e))
