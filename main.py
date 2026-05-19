"""main.py — FastAPI 服务入口"""

import asyncio
import json
import threading
import time
try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib  # Python < 3.11
import webbrowser
from dataclasses import asdict
from pathlib import Path
from typing import List

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

from alerter import Alerter
from advisor import advise_list
import advisor as _advisor_mod
from alert_history import record_alert
from killer import pause_process, resume_process, kill_process
from monitor import MetricsHistory, collect_metrics, collect_ai_processes

# ── 加载配置 ─────────────────────────────────────────────────
# py2app 打包后 __file__ 在 zip 内，需通过 sys.executable 定位 Resources 目录
import sys as _sys
def _find_base_dir() -> Path:
    exe = Path(_sys.executable)
    # py2app 结构：Contents/MacOS/python → Contents/Resources/
    resources = exe.parent.parent / "Resources"
    if (resources / "config.toml").exists():
        return resources
    return Path(__file__).parent

BASE_DIR = _find_base_dir()
with open(BASE_DIR / "config.toml", "rb") as f:
    CFG = tomllib.load(f)

SERVER_CFG   = CFG.get("server", {})
MONITOR_CFG  = CFG.get("monitor", {})
ALERT_CFG    = CFG.get("alert", {})
PROC_CFG     = CFG.get("processes", {})
AUTOKILL_CFG = CFG.get("auto_kill", {})

INTERVAL    = MONITOR_CFG.get("interval_sec", 1)
HISTORY_LEN = MONITOR_CFG.get("history_points", 150)
WATCH_KEYWORDS = PROC_CFG.get("watch_keywords", ["claude", "node", "python", "codex"])

# ── 全局状态 ─────────────────────────────────────────────────
history = MetricsHistory(maxlen=HISTORY_LEN)
alerter = Alerter(ALERT_CFG)
_latest_processes: list = []
_auto_kill_log: list = []       # 自动终止记录（最近20条）
_lock = threading.Lock()
_autokill_enabled = AUTOKILL_CFG.get("enabled", False)   # 运行时可动态切换

# ── 运行时可修改配置（热更新，写回 config.toml）────────────────
_settings = {
    "alert":    dict(ALERT_CFG),
    "auto_kill": dict(AUTOKILL_CFG),
    "monitor":  {"interval_sec": INTERVAL},
    "scoring":  {
        "cpu_caution_pct": _advisor_mod.CPU_CAUTION_PCT,
        "idle_min_hours":  _advisor_mod.IDLE_MIN_HOURS,
    },
}
_settings_lock = threading.Lock()

# ── 后台监控线程（1秒采集一次）───────────────────────────────
def _monitor_loop():
    while True:
        try:
            m = collect_metrics()
            level = alerter.check(m.to_dict())
            if level in ("warn", "crit"):
                record_alert(level, f"内存 {m.mem_percent:.0f}% / Swap {m.swap_percent:.0f}%")
            m.alert_level = level
            history.push(m)

            procs = collect_ai_processes(WATCH_KEYWORDS)
            with _lock:
                global _latest_processes
                _latest_processes = advise_list([asdict(p) for p in procs])
        except Exception as e:
            print(f"[monitor error] {e}")
        time.sleep(_settings["monitor"]["interval_sec"])


# ── 自动终止线程 ─────────────────────────────────────────────
def _auto_kill_loop():
    global _autokill_enabled
    last_killed_time = 0.0

    while True:
        time.sleep(5)  # 每5秒检查一次是否需要触发
        if not _autokill_enabled:
            continue

        # 每次循环重读配置，支持热更新
        with _settings_lock:
            ak = _settings["auto_kill"]
        mem_trigger  = ak.get("mem_trigger_pct", 85)
        swap_trigger = ak.get("swap_trigger_pct", 75)
        target_mem   = ak.get("target_mem_pct", 70)
        cooldown     = ak.get("cooldown_sec", 120)

        latest = history.latest
        if not latest:
            continue

        mem_pct  = latest.get("mem_percent", 0)
        swap_pct = latest.get("swap_percent", 0)

        if mem_pct < mem_trigger and swap_pct < swap_trigger:
            continue
        if time.time() - last_killed_time < cooldown:
            continue

        # 取当前 safe 进程，按内存从大到小
        with _lock:
            candidates = [p for p in _latest_processes if p.get("risk") == "safe"]
        candidates.sort(key=lambda p: p.get("mem_mb", 0), reverse=True)

        killed_count = 0
        freed_mb = 0.0
        for proc in candidates:
            # 重新检查内存是否已降下来
            cur = history.latest
            if cur and cur.get("mem_percent", 100) < target_mem:
                break
            pid = proc["pid"]
            result = kill_process(pid)
            if result.success:
                killed_count += 1
                freed_mb += result.mem_freed_mb
                log_entry = {
                    "ts": time.time(),
                    "pid": pid,
                    "name": proc.get("name", ""),
                    "mem_mb": proc.get("mem_mb", 0),
                    "reason": f"自动终止：内存 {mem_pct:.0f}% / Swap {swap_pct:.0f}%",
                }
                with _lock:
                    _auto_kill_log.append(log_entry)
                    if len(_auto_kill_log) > 20:
                        _auto_kill_log.pop(0)
                time.sleep(0.5)

        if killed_count:
            last_killed_time = time.time()
            print(f"[auto-kill] 自动终止 {killed_count} 个进程，释放约 {freed_mb:.0f} MB")


_monitor_thread   = threading.Thread(target=_monitor_loop,   daemon=True)
_autokill_thread  = threading.Thread(target=_auto_kill_loop, daemon=True)

# ── FastAPI App ──────────────────────────────────────────────
app = FastAPI(title="AI Guard", version="1.0.0")


@app.on_event("startup")
def on_startup():
    _monitor_thread.start()
    _autokill_thread.start()
    host = SERVER_CFG.get("host", "127.0.0.1")
    port = SERVER_CFG.get("port", 8765)
    import os
    if SERVER_CFG.get("open_browser", True) and not os.environ.get("AIGARD_NO_BROWSER"):
        threading.Timer(1.0, lambda: webbrowser.open(f"http://{host}:{port}")).start()


@app.get("/", response_class=HTMLResponse)
def index():
    html = (BASE_DIR / "web" / "index.html").read_text(encoding="utf-8")
    return HTMLResponse(html)


@app.get("/api/metrics")
def get_metrics():
    return history.latest or {}


@app.get("/api/history")
def get_history():
    return history.get_all()


@app.get("/api/processes")
def get_processes():
    with _lock:
        return list(_latest_processes)


@app.get("/api/autokill/log")
def get_autokill_log():
    with _lock:
        return list(_auto_kill_log)


@app.get("/api/alerts/history")
def get_alert_history():
    """返回最近 20 条 warn/crit 告警历史（来自 SQLite 持久化）"""
    from alert_history import get_recent_alerts
    return get_recent_alerts(20)


@app.get("/api/autokill/status")
def get_autokill_status():
    with _settings_lock:
        ak = _settings["auto_kill"]
    return {
        "enabled":          _autokill_enabled,
        "mem_trigger_pct":  ak.get("mem_trigger_pct", 85),
        "swap_trigger_pct": ak.get("swap_trigger_pct", 75),
        "target_mem_pct":   ak.get("target_mem_pct", 70),
        "cooldown_sec":     ak.get("cooldown_sec", 120),
    }


@app.post("/api/autokill/toggle")
def toggle_autokill():
    """运行时动态开启 / 关闭自动终止，无需重启"""
    global _autokill_enabled
    with _lock:
        _autokill_enabled = not _autokill_enabled
        state = _autokill_enabled
    label = "开启" if state else "关闭"
    print(f"[auto-kill] 自动终止已{label}")
    return {"enabled": state}


# ── 设置接口 ─────────────────────────────────────────────────
@app.get("/api/settings")
def get_settings():
    with _settings_lock:
        return dict(_settings)


class SettingsPatch(BaseModel):
    alert:    dict = {}
    auto_kill: dict = {}
    monitor:  dict = {}
    scoring:  dict = {}


@app.post("/api/settings")
def save_settings(payload: SettingsPatch):
    """保存并立即应用所有可配置项，同时写回 config.toml"""
    global _settings
    with _settings_lock:
        for group in ("alert", "auto_kill", "monitor", "scoring"):
            patch = getattr(payload, group)
            if patch:
                _settings[group].update(patch)

        # 立即应用 alerter 告警阈值
        a = _settings["alert"]
        alerter.mem_warn          = a.get("mem_warn",          alerter.mem_warn)
        alerter.mem_crit          = a.get("mem_crit",          alerter.mem_crit)
        alerter.swap_warn         = a.get("swap_warn",         alerter.swap_warn)
        alerter.swap_crit         = a.get("swap_crit",         alerter.swap_crit)
        alerter.disk_free_warn_gb = a.get("disk_free_warn_gb", alerter.disk_free_warn_gb)
        alerter.disk_free_crit_gb = a.get("disk_free_crit_gb", alerter.disk_free_crit_gb)
        alerter.cooldown_sec      = a.get("cooldown_sec",      alerter.cooldown_sec)

        # 立即应用 advisor 评分参数
        sc = _settings["scoring"]
        _advisor_mod.CPU_CAUTION_PCT = sc.get("cpu_caution_pct", _advisor_mod.CPU_CAUTION_PCT)
        _advisor_mod.IDLE_MIN_HOURS  = sc.get("idle_min_hours",  _advisor_mod.IDLE_MIN_HOURS)
        # auto_kill 和 monitor 间隔：下次循环自动生效

    _persist_settings()
    return {"ok": True}


def _persist_settings():
    """将当前 _settings 写回 config.toml（保留原有 server/processes 等不变）"""
    import tomli_w
    with _settings_lock:
        merged = dict(CFG)
        merged["alert"]    = dict(_settings["alert"])
        merged["auto_kill"] = dict(_settings["auto_kill"])
        merged["monitor"]  = {**dict(MONITOR_CFG),
                               "interval_sec": _settings["monitor"]["interval_sec"]}
    with open(BASE_DIR / "config.toml", "wb") as f:
        tomli_w.dump(merged, f)


@app.get("/api/stream")
async def stream():
    """SSE 实时推流（1秒一次，无缓存）"""
    async def event_generator():
        while True:
            latest = history.latest
            with _lock:
                procs = list(_latest_processes)
                log   = list(_auto_kill_log[-5:])
            payload = json.dumps({
                "metrics":        latest,
                "processes":      procs,
                "auto_kill_log":  log,
                "autokill_enabled": _autokill_enabled,
            }, ensure_ascii=False)
            yield f"data: {payload}\n\n"
            await asyncio.sleep(_settings["monitor"]["interval_sec"])

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-store",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# ── 批量操作（必须在 {pid} 路由之前定义，避免路由冲突）──────────
class BatchRequest(BaseModel):
    pids: List[int]


@app.post("/api/processes/batch/kill")
def batch_kill(req: BatchRequest):
    """批量终止指定 PID 列表"""
    results = []
    total_freed = 0.0
    for pid in req.pids:
        r = kill_process(pid)
        results.append({"pid": pid, "success": r.success, "message": r.message})
        if r.success:
            total_freed += r.mem_freed_mb
    return {"results": results, "total_freed_mb": round(total_freed, 1)}


@app.post("/api/processes/batch/pause")
def batch_pause(req: BatchRequest):
    """批量暂停指定 PID 列表"""
    results = []
    for pid in req.pids:
        r = pause_process(pid)
        results.append({"pid": pid, "success": r.success, "message": r.message})
    return {"results": results}


@app.post("/api/processes/batch/kill-safe")
def batch_kill_safe():
    """一键终止所有评分为 safe 的进程"""
    with _lock:
        safe_procs = [p for p in _latest_processes if p.get("risk") == "safe"]
    results = []
    total_freed = 0.0
    for proc in safe_procs:
        pid = proc["pid"]
        r = kill_process(pid)
        results.append({
            "pid": pid,
            "name": proc.get("name", ""),
            "mem_mb": proc.get("mem_mb", 0),
            "success": r.success,
            "message": r.message,
        })
        if r.success:
            total_freed += r.mem_freed_mb
    return {
        "killed": len([r for r in results if r["success"]]),
        "total_freed_mb": round(total_freed, 1),
        "results": results,
    }


# ── 单进程操作 ────────────────────────────────────────────────
@app.post("/api/processes/{pid}/pause")
def api_pause(pid: int):
    result = pause_process(pid)
    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)
    return {"message": result.message, "mem_freed_mb": result.mem_freed_mb}


@app.post("/api/processes/{pid}/resume")
def api_resume(pid: int):
    result = resume_process(pid)
    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)
    return {"message": result.message}


@app.post("/api/processes/{pid}/kill")
def api_kill(pid: int):
    result = kill_process(pid)
    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)
    return {"message": result.message, "mem_freed_mb": result.mem_freed_mb}


# ── 启动函数（供外部 import 调用）──────────────────────────────
def start_server(host: str = None, port: int = None):
    """供外部调用（如 rumps App）的启动函数，在当前线程阻塞运行。"""
    _host = host or SERVER_CFG.get("host", "127.0.0.1")
    _port = port or SERVER_CFG.get("port", 8765)
    print(f"AI Guard 服务启动中 → http://{_host}:{_port}")
    uvicorn.run(app, host=_host, port=_port, log_level="warning")


# ── 入口 ─────────────────────────────────────────────────────
if __name__ == "__main__":
    start_server()
