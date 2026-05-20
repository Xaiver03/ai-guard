"""
FastAPI 路由定义
"""

import asyncio
import json
from pathlib import Path
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

from aigard.core import pause_process, resume_process, kill_process


def create_app(base_dir: Path, threads_manager) -> FastAPI:
    """创建 FastAPI 应用实例"""
    app = FastAPI(title="AI Guard", version="1.0.0")

    # ── 首页 ──────────────────────────────────────────────────
    @app.get("/", response_class=HTMLResponse)
    def index():
        # 开发模式：base_dir 是项目根目录
        # py2app 打包后：base_dir 是 Contents/Resources/
        dev_path = base_dir / "aigard" / "ui" / "index.html"
        pkg_path = base_dir / "ui" / "index.html"
        html_path = dev_path if dev_path.exists() else pkg_path
        html = html_path.read_text(encoding="utf-8")
        return HTMLResponse(html)

    # ── 指标和历史 ────────────────────────────────────────────
    @app.get("/api/metrics")
    def get_metrics():
        return threads_manager.history.latest or {}

    @app.get("/api/history")
    def get_history():
        return threads_manager.history.get_all()

    @app.get("/api/processes")
    def get_processes():
        with threads_manager.lock:
            return list(threads_manager.latest_processes)

    @app.get("/api/autokill/log")
    def get_autokill_log():
        with threads_manager.lock:
            return list(threads_manager.auto_kill_log)

    @app.get("/api/alerts/history")
    def get_alert_history():
        """返回最近 20 条 warn/crit 告警历史"""
        from alert_history import get_recent_alerts
        return get_recent_alerts(20)

    # ── 自动终止控制 ──────────────────────────────────────────
    @app.get("/api/autokill/status")
    def get_autokill_status():
        with threads_manager.settings_lock:
            ak = threads_manager.settings["auto_kill"]
        return {
            "enabled": threads_manager.autokill_enabled,
            "mem_trigger_pct": ak.get("mem_trigger_pct", 85),
            "swap_trigger_pct": ak.get("swap_trigger_pct", 75),
            "target_mem_pct": ak.get("target_mem_pct", 70),
            "cooldown_sec": ak.get("cooldown_sec", 120),
        }

    @app.post("/api/autokill/toggle")
    def toggle_autokill():
        """运行时动态开启/关闭自动终止"""
        with threads_manager.lock:
            threads_manager.autokill_enabled = not threads_manager.autokill_enabled
            state = threads_manager.autokill_enabled
        label = "开启" if state else "关闭"
        print(f"[auto-kill] 自动终止已{label}")
        return {"enabled": state}

    # ── 设置管理 ──────────────────────────────────────────────
    @app.get("/api/settings")
    def get_settings():
        with threads_manager.settings_lock:
            return dict(threads_manager.settings)

    class SettingsPatch(BaseModel):
        alert: dict = {}
        auto_kill: dict = {}
        monitor: dict = {}
        scoring: dict = {}

    @app.post("/api/settings")
    def save_settings(payload: SettingsPatch):
        """保存并立即应用所有可配置项"""
        import aigard.core.advisor as _advisor_mod
        import tomli_w

        with threads_manager.settings_lock:
            for group in ("alert", "auto_kill", "monitor", "scoring"):
                patch = getattr(payload, group)
                if patch:
                    threads_manager.settings[group].update(patch)

            # 立即应用 alerter 告警阈值
            a = threads_manager.settings["alert"]
            threads_manager.alerter.mem_warn = a.get("mem_warn", threads_manager.alerter.mem_warn)
            threads_manager.alerter.mem_crit = a.get("mem_crit", threads_manager.alerter.mem_crit)
            threads_manager.alerter.swap_warn = a.get("swap_warn", threads_manager.alerter.swap_warn)
            threads_manager.alerter.swap_crit = a.get("swap_crit", threads_manager.alerter.swap_crit)
            threads_manager.alerter.disk_free_warn_gb = a.get("disk_free_warn_gb", threads_manager.alerter.disk_free_warn_gb)
            threads_manager.alerter.disk_free_crit_gb = a.get("disk_free_crit_gb", threads_manager.alerter.disk_free_crit_gb)
            threads_manager.alerter.cooldown_sec = a.get("cooldown_sec", threads_manager.alerter.cooldown_sec)

            # 立即应用 advisor 评分参数
            sc = threads_manager.settings["scoring"]
            _advisor_mod.CPU_CAUTION_PCT = sc.get("cpu_caution_pct", _advisor_mod.CPU_CAUTION_PCT)
            _advisor_mod.IDLE_MIN_HOURS = sc.get("idle_min_hours", _advisor_mod.IDLE_MIN_HOURS)

            # 写回 config.toml
            merged = dict(threads_manager.config)
            merged["alert"] = dict(threads_manager.settings["alert"])
            merged["auto_kill"] = dict(threads_manager.settings["auto_kill"])
            merged["monitor"] = {
                **dict(threads_manager.config.get("monitor", {})),
                "interval_sec": threads_manager.settings["monitor"]["interval_sec"]
            }

        # 开发模式 vs py2app 打包后的路径
        dev_path = base_dir / "config.toml"
        pkg_path = base_dir.parent / "config.toml"
        config_path = dev_path if dev_path.exists() else pkg_path
        with open(config_path, "wb") as f:
            tomli_w.dump(merged, f)

        return {"ok": True}

    # ── SSE 实时流 ────────────────────────────────────────────
    @app.get("/api/stream")
    async def stream():
        """SSE 实时推流"""
        async def event_generator():
            while True:
                latest = threads_manager.history.latest
                with threads_manager.lock:
                    procs = list(threads_manager.latest_processes)
                    log = list(threads_manager.auto_kill_log[-5:])
                    blocked = sorted(list(threads_manager.blocked_processes))
                payload = json.dumps({
                    "metrics": latest,
                    "processes": procs,
                    "auto_kill_log": log,
                    "autokill_enabled": threads_manager.autokill_enabled,
                    "blocked_processes": blocked,
                }, ensure_ascii=False)
                yield f"data: {payload}\n\n"

                with threads_manager.settings_lock:
                    interval = threads_manager.settings.get("monitor", {}).get("interval_sec", 1)
                await asyncio.sleep(interval)

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-store",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive",
            },
        )

    # ── 批量操作 ──────────────────────────────────────────────
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
        with threads_manager.lock:
            safe_procs = [p for p in threads_manager.latest_processes if p.get("risk") == "safe"]
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

    # ── 单进程操作 ────────────────────────────────────────────
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

    # ── 黑名单管理 ────────────────────────────────────────────
    @app.post("/api/processes/block")
    def block_process(req: dict):
        """将进程名加入启动拦截黑名单"""
        name = req.get("name", "").strip().lower()
        if not name:
            raise HTTPException(status_code=400, detail="进程名不能为空")
        with threads_manager.lock:
            threads_manager.blocked_processes.add(name)
        return {"message": f"已将 {name} 加入黑名单", "blocked": list(threads_manager.blocked_processes)}

    @app.post("/api/processes/unblock")
    def unblock_process(req: dict):
        """将进程名移出黑名单"""
        name = req.get("name", "").strip().lower()
        with threads_manager.lock:
            threads_manager.blocked_processes.discard(name)
        return {"message": f"已将 {name} 移出黑名单", "blocked": list(threads_manager.blocked_processes)}

    @app.get("/api/processes/blocked")
    def get_blocked():
        """获取当前黑名单列表"""
        with threads_manager.lock:
            return {"blocked": sorted(list(threads_manager.blocked_processes))}

    @app.post("/api/processes/blocked/clear")
    def clear_blocked():
        """清空黑名单"""
        with threads_manager.lock:
            threads_manager.blocked_processes.clear()
        return {"message": "已清空黑名单", "blocked": []}

    # ── 定时终止配置 ──────────────────────────────────────────
    @app.get("/api/scheduled-kill/status")
    def get_scheduled_kill_status():
        """获取定时终止配置"""
        return {
            "enabled": threads_manager.scheduled_kill_enabled,
            "interval_minutes": threads_manager.scheduled_kill_interval,
        }

    @app.post("/api/scheduled-kill/config")
    def set_scheduled_kill_config(req: dict):
        """更新定时终止配置"""
        if "enabled" in req:
            threads_manager.scheduled_kill_enabled = bool(req["enabled"])
        if "interval_minutes" in req:
            interval = int(req["interval_minutes"])
            if interval < 1:
                raise HTTPException(status_code=400, detail="间隔必须 >= 1 分钟")
            threads_manager.scheduled_kill_interval = interval
        return {
            "message": "定时终止配置已更新",
            "enabled": threads_manager.scheduled_kill_enabled,
            "interval_minutes": threads_manager.scheduled_kill_interval,
        }

    return app
