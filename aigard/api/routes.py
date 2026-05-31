"""
# [CN] FastAPI 路由定义
"""

import asyncio
import json
import time
import threading
from pathlib import Path
from typing import List, Dict, Optional, Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from aigard.core import pause_process, resume_process, kill_process


# [CN] ── 数据缓存和防抖 ────────────────────────────────────────────
class DataCache:
    # [CN] """数据缓存,支持防抖(90秒 TTL 减少重复扫描)"""
    def __init__(self, ttl: int = 90):
        self.ttl = ttl
        self._cache: Dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Optional[Any]:
        # [CN] """获取缓存数据,过期返回 None"""
        if key not in self._cache:
            return None
        timestamp, data = self._cache[key]
        if time.time() - timestamp > self.ttl:
            del self._cache[key]
            return None
        return data

    def set(self, key: str, data: Any):
        """SettingsCacheData"""
        self._cache[key] = (time.time(), data)

    def clear(self, key: str):
        # [CN] """清除指定缓存"""
        self._cache.pop(key, None)


# [CN] 全局缓存实例(90秒 TTL)
_data_cache = DataCache(ttl=90)


def create_app(base_dir: Path, threads_manager) -> FastAPI:
    # [CN] """创建 FastAPI 应用实例"""
    app = FastAPI(title="AI Guard", version="1.0.0")

    # 懒加载标记
    _routers_loaded = {"whitelist": False, "bookmarks": False, "bookmarks_v2": False, "usage": False}
    _routers_lock = threading.Lock()

    # 注册白名单路由(轻量级,立即加载)
    from aigard.api.whitelist import router as whitelist_router
    app.include_router(whitelist_router)
    _routers_loaded["whitelist"] = True

    # 懒加载中间件:按需加载重量级路由
    @app.middleware("http")
    async def lazy_load_middleware(request, call_next):
        path = request.url.path

        # 书签管理路由 v1(旧版,浏览器导入)
        if not _routers_loaded["bookmarks"] and (
            path.startswith("/api/bookmarks") and not path.startswith("/api/bookmarks/v2")
            or path == "/bookmarks.html"
        ):
            with _routers_lock:
                if not _routers_loaded["bookmarks"]:
                    from aigard.api.bookmarks import router as bookmarks_router
                    app.include_router(bookmarks_router)
                    _routers_loaded["bookmarks"] = True

        # 书签管理路由 v2(新版,OneNav 风格)
        if not _routers_loaded["bookmarks_v2"] and path.startswith("/api/bookmarks/v2"):
            with _routers_lock:
                if not _routers_loaded["bookmarks_v2"]:
                    from aigard.api.bookmarks_v2 import router as bookmarks_v2_router
                    app.include_router(bookmarks_v2_router)
                    _routers_loaded["bookmarks_v2"] = True

        # Claude 使用统计路由(重量级)
        if not _routers_loaded["usage"] and (
            path.startswith("/api/usage") or path == "/usage.html"
        ):
            with _routers_lock:
                if not _routers_loaded["usage"]:
                    from aigard.api.usage import router as usage_router
                    app.include_router(usage_router)
                    _routers_loaded["usage"] = True

        return await call_next(request)

    # [CN] # ── 首页 ──────────────────────────────────────────────────
    @app.get("/", response_class=HTMLResponse)
    def index():
        # [CN] # 开发模式:base_dir 是项目根目录
        # [CN] # py2app 打包后:base_dir 是 Contents/Resources/
        dev_path = base_dir / "aigard" / "ui" / "index.html"
        pkg_path = base_dir / "ui" / "index.html"
        html_path = dev_path if dev_path.exists() else pkg_path
        html = html_path.read_text(encoding="utf-8")
        return HTMLResponse(html)

    # ── 书签管理页面 ──────────────────────────────────────────
    @app.get("/bookmarks.html", response_class=HTMLResponse)
    def bookmarks_page():
        dev_path = base_dir / "aigard" / "ui" / "bookmarks.html"
        pkg_path = base_dir / "ui" / "bookmarks.html"
        html_path = dev_path if dev_path.exists() else pkg_path
        html = html_path.read_text(encoding="utf-8")
        return HTMLResponse(html)

    # ── 书签管理页面 v2 (OneNav 风格) ────────────────────────────
    @app.get("/bookmarks_v2.html", response_class=HTMLResponse)
    def bookmarks_v2_page():
        dev_path = base_dir / "aigard" / "ui" / "bookmarks_v2.html"
        pkg_path = base_dir / "ui" / "bookmarks_v2.html"
        html_path = dev_path if dev_path.exists() else pkg_path
        html = html_path.read_text(encoding="utf-8")
        return HTMLResponse(html)

    # [CN] # ── Claude 使用统计页面 ──────────────────────────────────
    @app.get("/usage.html", response_class=HTMLResponse)
    def usage_page():
        dev_path = base_dir / "aigard" / "ui" / "usage.html"
        pkg_path = base_dir / "ui" / "usage.html"
        html_path = dev_path if dev_path.exists() else pkg_path
        html = html_path.read_text(encoding="utf-8")
        return HTMLResponse(html)

    # [CN] # ── Popover 页面 ──────────────────────────────────────────
    @app.get("/popover.html", response_class=HTMLResponse)
    def popover_page():
        dev_path = base_dir / "aigard" / "ui" / "popover.html"
        pkg_path = base_dir / "ui" / "popover.html"
        html_path = dev_path if dev_path.exists() else pkg_path
        html = html_path.read_text(encoding="utf-8")
        return HTMLResponse(html)

    # [CN] # ── 工具导航页面 ──────────────────────────────────────────
    @app.get("/tools.html", response_class=HTMLResponse)
    def tools_page():
        dev_path = base_dir / "aigard" / "ui" / "tools.html"
        pkg_path = base_dir / "ui" / "tools.html"
        html_path = dev_path if dev_path.exists() else pkg_path
        html = html_path.read_text(encoding="utf-8")
        return HTMLResponse(html)

    # [CN] # ── 最佳实践页面 ──────────────────────────────────────────
    @app.get("/practices.html", response_class=HTMLResponse)
    def practices_page():
        dev_path = base_dir / "aigard" / "ui" / "practices.html"
        pkg_path = base_dir / "ui" / "practices.html"
        html_path = dev_path if dev_path.exists() else pkg_path
        html = html_path.read_text(encoding="utf-8")
        return HTMLResponse(html)

    @app.get("/settings.html", response_class=HTMLResponse)
    def settings_page():
        dev_path = base_dir / "aigard" / "ui" / "settings.html"
        pkg_path = base_dir / "ui" / "settings.html"
        html_path = dev_path if dev_path.exists() else pkg_path
        html = html_path.read_text(encoding="utf-8")
        return HTMLResponse(html)

    @app.get("/about.html", response_class=HTMLResponse)
    def about_page():
        dev_path = base_dir / "aigard" / "ui" / "about.html"
        pkg_path = base_dir / "ui" / "about.html"
        html_path = dev_path if dev_path.exists() else pkg_path
        html = html_path.read_text(encoding="utf-8")
        return HTMLResponse(html)

    # [CN] # ── 工具导航 API ──────────────────────────────────────────
    @app.get("/api/tools")
    def get_tools():
        # [CN] """获取工具列表"""
        import json
        import sys
        from pathlib import Path

        # [CN] 开发模式:base_dir 是项目根目录
        dev_path = base_dir / "aigard" / "data" / "tools.json"
        # [CN] py2app 打包后:base_dir 是 Contents/Resources/
        pkg_path = base_dir / "data" / "tools.json"

        # [CN] 兜底:直接从当前文件位置查找
        fallback_path = Path(__file__).parent.parent / "data" / "tools.json"

        data_path = None
        if dev_path.exists():
            data_path = dev_path
        elif pkg_path.exists():
            data_path = pkg_path
        elif fallback_path.exists():
            data_path = fallback_path

        if data_path is None or not data_path.exists():
            # [CN] print(f"[tools] 未找到数据文件")
            # TODO: Translate this log message
            print(f"[tools] base_dir: {base_dir}")
            print(f"[tools] dev_path: {dev_path} (exists: {dev_path.exists()})")
            print(f"[tools] pkg_path: {pkg_path} (exists: {pkg_path.exists()})")
            print(f"[tools] fallback_path: {fallback_path} (exists: {fallback_path.exists()})")
            return {"tools": []}

        with open(data_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    # [CN] ── 最佳实践 API ──────────────────────────────────────────
    @app.get("/api/practices")
    def get_practices():
        # [CN] """获取最佳实践列表"""
        import json
        from pathlib import Path

        # [CN] # 开发模式:base_dir 是项目根目录
        dev_path = base_dir / "aigard" / "data" / "practices.json"
        # [CN] # py2app 打包后:base_dir 是 Contents/Resources/
        pkg_path = base_dir / "data" / "practices.json"

        # [CN] # 兜底:直接从当前文件位置查找
        fallback_path = Path(__file__).parent.parent / "data" / "practices.json"

        data_path = None
        if dev_path.exists():
            data_path = dev_path
        elif pkg_path.exists():
            data_path = pkg_path
        elif fallback_path.exists():
            data_path = fallback_path

        if data_path is None or not data_path.exists():
            # [CN] print(f"[practices] 未找到数据文件")
            return {"categories": []}

        with open(data_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    # [CN] # ── 指标和历史 ────────────────────────────────────────────
    @app.get("/api/metrics")
    def get_metrics():
        # [CN] """获取当前指标(无缓存,实时数据)"""
        return threads_manager.history.latest or {}

    @app.get("/api/history")
    def get_history():
        """GetHistoryData(NoneCache,Real-timeData)"""
        return threads_manager.history.get_all()

    @app.get("/api/processes")
    def get_processes():
        # [CN] """获取 AI 进程列表(60秒缓存)"""
        # [CN] 尝试从缓存获取
        cached = _data_cache.get("processes")
        if cached is not None:
            return cached

        # [CN] 重新计算
        with threads_manager.lock:
            processes = list(threads_manager.latest_processes)

        # [CN] 为每个进程添加白名单标记
        import main as _main_mod
        for proc in processes:
            proc["whitelisted"] = _main_mod.whitelist.is_whitelisted(proc)

        # CacheResult
        _data_cache.set("processes", processes)
        return processes

    @app.get("/api/processes/all")
    def get_all_processes():
        # [CN] """获取所有进程(类似活动监视器,60秒缓存)"""
        # [CN] # 尝试从缓存获取
        cached = _data_cache.get("all_processes")
        if cached is not None:
            return cached

        from aigard.core import collect_all_processes
        import aigard.core.advisor as _advisor_mod
        import main as _main_mod

        all_procs = collect_all_processes()
        result = []
        for proc in all_procs:
            proc_dict = {
                "pid": proc.pid,
                "name": proc.name,
                "cmdline": proc.cmdline,
                "mem_mb": proc.mem_mb,
                "cpu_percent": proc.cpu_percent,
                "status": proc.status,
                "create_time": proc.create_time,
            }
            # [CN] # 评分和建议
            advice = _advisor_mod.advise(proc_dict)
            proc_dict["risk"] = advice.risk
            proc_dict["risk_label"] = advice.label
            proc_dict["risk_reasons"] = advice.reasons
            proc_dict["suggested_action"] = advice.action
            # [CN] # 白名单标记
            proc_dict["whitelisted"] = _main_mod.whitelist.is_whitelisted(proc_dict)
            result.append(proc_dict)

        # CacheResult
        _data_cache.set("all_processes", result)
        return result

    @app.get("/api/autokill/log")
    def get_autokill_log():
        with threads_manager.lock:
            return list(threads_manager.auto_kill_log)

    @app.get("/api/alerts/history")
    def get_alert_history():
        # [CN] """返回最近 20 条 warn/crit 告警历史"""
        from alert_history import get_recent_alerts
        return get_recent_alerts(20)

    # [CN] ── 缓存管理 ──────────────────────────────────────────────
    @app.post("/api/cache/clear")
    def clear_cache():
        """ClearAllCache,MandatoryRefreshData"""
        _data_cache._cache.clear()
        return {"status": "ok", "message": "缓存已清除"}

    @app.get("/api/cache/stats")
    def get_cache_stats():
        """GetCacheStatisticsInfo"""
        stats = {}
        for key, (timestamp, _) in _data_cache._cache.items():
            age = time.time() - timestamp
            stats[key] = {
                "age_seconds": round(age, 1),
                "expires_in": round(_data_cache.ttl - age, 1)
            }
        return stats

    # ── AutomaticUpdate ──────────────────────────────────────────────
    @app.get("/api/update/check")
    def check_update():
        # [CN] """检查是否有新版本"""
        from aigard.updater import UpdateChecker
        checker = UpdateChecker()
        result = checker.check_update()
        if result is None:
            raise HTTPException(status_code=503, detail="无法连接到 GitHub")
        return result

    @app.get("/api/update/current-version")
    def get_current_version():
        # [CN] """获取当前版本号"""
        from aigard.updater import CURRENT_VERSION
        return {"version": CURRENT_VERSION}

    # [CN] ── 自动终止控制 ──────────────────────────────────────────
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
        # [CN] """运行时动态开启/关闭自动终止"""
        with threads_manager.lock:
            threads_manager.autokill_enabled = not threads_manager.autokill_enabled
            state = threads_manager.autokill_enabled
        # [CN] # 启用时唤醒自动终止线程
        if state:
            threads_manager._autokill_event.set()
        # [CN] label = "开启" if state else "关闭"
        # [CN] print(f"[auto-kill] 自动终止已{label}")
        return {"enabled": state}

    # [CN] # ── 设置管理 ──────────────────────────────────────────────
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
        # [CN] """保存并立即应用所有可配置项"""
        import aigard.core.advisor as _advisor_mod
        import tomli_w

        with threads_manager.settings_lock:
            for group in ("alert", "auto_kill", "monitor", "scoring"):
                patch = getattr(payload, group)
                if patch:
                    threads_manager.settings[group].update(patch)

            # [CN] 立即应用 alerter 告警阈值
            a = threads_manager.settings["alert"]
            threads_manager.alerter.mem_warn = a.get("mem_warn", threads_manager.alerter.mem_warn)
            threads_manager.alerter.mem_crit = a.get("mem_crit", threads_manager.alerter.mem_crit)
            threads_manager.alerter.swap_warn = a.get("swap_warn", threads_manager.alerter.swap_warn)
            threads_manager.alerter.swap_crit = a.get("swap_crit", threads_manager.alerter.swap_crit)
            threads_manager.alerter.disk_free_warn_gb = a.get("disk_free_warn_gb", threads_manager.alerter.disk_free_warn_gb)
            threads_manager.alerter.disk_free_crit_gb = a.get("disk_free_crit_gb", threads_manager.alerter.disk_free_crit_gb)
            threads_manager.alerter.cooldown_sec = a.get("cooldown_sec", threads_manager.alerter.cooldown_sec)

            # [CN] 立即应用 advisor 评分参数
            sc = threads_manager.settings["scoring"]
            _advisor_mod.CPU_CAUTION_PCT = sc.get("cpu_caution_pct", _advisor_mod.CPU_CAUTION_PCT)
            _advisor_mod.IDLE_MIN_HOURS = sc.get("idle_min_hours", _advisor_mod.IDLE_MIN_HOURS)

            # [CN] 写回 config.toml
            merged = dict(threads_manager.config)
            merged["alert"] = dict(threads_manager.settings["alert"])
            merged["auto_kill"] = dict(threads_manager.settings["auto_kill"])
            merged["monitor"] = {
                **dict(threads_manager.config.get("monitor", {})),
                "interval_sec": threads_manager.settings["monitor"]["interval_sec"]
            }

        # [CN] 开发模式 vs py2app 打包后的路径
        # [CN] py2app 打包后 base_dir 指向 Resources/,config.toml 也在 Resources/
        dev_path = base_dir / "config.toml"
        pkg_path = base_dir.parent / "config.toml"
        # [CN] 如果 base_dir 是 zip 内路径(py2app 将代码打包进 zip),需要找到 Resources/
        if not dev_path.exists() and not pkg_path.exists():
            import sys
            exe = Path(sys.executable)
            if "Contents/MacOS" in str(exe):
                resources = exe.parent.parent / "Resources"
                res_path = resources / "config.toml"
                if res_path.exists():
                    config_path = res_path
                else:
                    config_path = dev_path  # fallback
            else:
                config_path = dev_path
        else:
            config_path = dev_path if dev_path.exists() else pkg_path
        with open(config_path, "wb") as f:
            tomli_w.dump(merged, f)

        return {"ok": True}

    # [CN] ── SSE 实时流 ────────────────────────────────────────────
    @app.get("/api/stream")
    async def stream():
        # [CN] """SSE 实时推流(变化检测 + 3秒间隔)"""
        async def event_generator():
            _last_payload = None
            while True:
                latest = threads_manager.history.latest
                with threads_manager.lock:
                    procs = list(threads_manager.latest_processes)
                    log = list(threads_manager.auto_kill_log[-5:])
                    blocked = sorted(list(threads_manager.blocked_processes))

                # [CN] # 变化检测:只在数据实际变化时序列化和推送
                snapshot_key = (
                    latest.get("ts") if latest else None,
                    latest.get("cpu_percent") if latest else None,
                    latest.get("mem_percent") if latest else None,
                    len(procs),
                    tuple(p.get("pid", 0) for p in procs[:20]),
                    len(log),
                    threads_manager.autokill_enabled,
                    tuple(blocked),
                )
                current_hash = hash(snapshot_key)

                if _last_payload is None or current_hash != getattr(event_generator, '_last_hash', None):
                    payload = json.dumps({
                        "metrics": latest,
                        "processes": procs,
                        "auto_kill_log": log,
                        "autokill_enabled": threads_manager.autokill_enabled,
                        "blocked_processes": blocked,
                    }, ensure_ascii=False)
                    _last_payload = payload
                    event_generator._last_hash = current_hash
                    yield f"data: {payload}\n\n"
                else:
                    # [CN] # 心跳保持连接
                    yield f": heartbeat\n\n"

                await asyncio.sleep(15)

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-store",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive",
            },
        )

    # [CN] # ── 批量操作 ──────────────────────────────────────────────
    class BatchRequest(BaseModel):
        pids: List[int]

    @app.post("/api/processes/batch/kill")
    def batch_kill(req: BatchRequest):
        # [CN] """批量终止指定 PID 列表"""
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
        # [CN] """批量暂停指定 PID 列表"""
        results = []
        for pid in req.pids:
            r = pause_process(pid)
            results.append({"pid": pid, "success": r.success, "message": r.message})
        return {"results": results}

    @app.post("/api/processes/batch/kill-safe")
    def batch_kill_safe():
        # [CN] """一键终止所有评分为 safe 的进程(排除当前进程)"""
        import os
        current_pid = os.getpid()

        with threads_manager.lock:
            # [CN] 排除当前进程
            safe_procs = [
                p for p in threads_manager.latest_processes
                if p.get("risk") == "safe" and p["pid"] != current_pid
            ]
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
            "killed_count": len([r for r in results if r["success"]]),  # [CN] 兼容前端
            "total_freed_mb": round(total_freed, 1),
            "results": results,
        }

    # [CN] ── 单进程操作 ────────────────────────────────────────────
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

    # [CN] ── 黑名单管理 ────────────────────────────────────────────
    @app.post("/api/processes/block")
    def block_process(req: dict):
        """将进程名加入启动拦截黑名单"""
        name = req.get("name", "").strip().lower()
        if not name:
            raise HTTPException(status_code=400, detail="进程名不能为空")
        with threads_manager.lock:
            threads_manager.blocked_processes.add(name)
        # [CN] # 唤醒黑名单线程
        threads_manager._block_event.set()
        return {"message": f"已将 {name} 加入黑名单", "blocked": list(threads_manager.blocked_processes)}

    @app.post("/api/processes/unblock")
    def unblock_process(req: dict):
        # [CN] """将进程名移出黑名单"""
        name = req.get("name", "").strip().lower()
        with threads_manager.lock:
            threads_manager.blocked_processes.discard(name)
        return {"message": f"已将 {name} 移出黑名单", "blocked": list(threads_manager.blocked_processes)}

    @app.get("/api/processes/blocked")
    def get_blocked():
        # [CN] """获取当前黑名单列表"""
        with threads_manager.lock:
            return {"blocked": sorted(list(threads_manager.blocked_processes))}

    @app.post("/api/processes/blocked/clear")
    def clear_blocked():
        # [CN] """清空黑名单"""
        with threads_manager.lock:
            threads_manager.blocked_processes.clear()
        return {"message": "已清空黑名单", "blocked": []}

    # ── TimerTerminateConfiguration ──────────────────────────────────────────
    @app.get("/api/scheduled-kill/status")
    def get_scheduled_kill_status():
        """GetTimerTerminateConfiguration"""
        return {
            "enabled": threads_manager.scheduled_kill_enabled,
            "interval_minutes": threads_manager.scheduled_kill_interval,
        }

    @app.post("/api/scheduled-kill/config")
    def set_scheduled_kill_config(req: dict):
        """UpdateTimerTerminateConfiguration"""
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

    # [CN] ── 系统操作 ──────────────────────────────────────────────
    @app.post("/api/system/open-privacy-settings")
    def open_privacy_settings():
        # [CN] """打开 macOS 系统设置 → 隐私与安全性 → 完全磁盘访问权限"""
        import subprocess
        try:
            subprocess.run(
                ["open", "x-apple.systempreferences:com.apple.preference.security?Privacy_AllFiles"],
                check=False, timeout=5
            )
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": "无法打开系统设置"}

    # ── StaticFile(CSS / JS)────────────────────────────────────
    ui_dev = base_dir / "aigard" / "ui"
    ui_pkg = base_dir / "ui"
    ui_dir = ui_dev if ui_dev.exists() else ui_pkg

    css_dir = ui_dir / "css"
    js_dir = ui_dir / "js"
    if css_dir.exists():
        app.mount("/css", StaticFiles(directory=str(css_dir)), name="css")
    if js_dir.exists():
        app.mount("/js", StaticFiles(directory=str(js_dir)), name="js")

    # ── Launch Dashboard Apply ──────────────────────────────────
    @app.post("/api/launch/dashboard")
    def launch_dashboard():
        # [CN] """显示监控面板窗口"""
        try:
            # [CN] 通过主应用显示窗口
            import objc
            from AppKit import NSApp

            # [CN] 获取主应用的 delegate
            delegate = NSApp.delegate()
            if delegate and hasattr(delegate, 'dashboard_window'):
                delegate.dashboard_window.show()
                return {"success": True, "message": "监控面板已打开"}
            else:
                raise Exception("无法访问窗口管理器")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"打开失败: {str(e)}")

    return app
