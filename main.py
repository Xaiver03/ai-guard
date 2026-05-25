"""
AI Guard - 智能内存守护
主入口文件
"""

import os
import sys
import threading
import webbrowser
from pathlib import Path

import tomli
import asyncio
from hypercorn.config import Config
from hypercorn.asyncio import serve

from aigard.core import MetricsHistory, Alerter, WhitelistManager
from aigard.core.threads import BackgroundThreads
from aigard.api import create_app


# ── 配置加载 ──────────────────────────────────────────────────
def _find_config() -> Path:
    """查找 config.toml，支持开发模式和 py2app 打包模式"""
    # 1. 开发模式：与 main.py 同级
    dev_path = Path(__file__).parent / "config.toml"
    if dev_path.exists():
        return dev_path

    # 2. py2app 打包模式：Resources/ 目录
    # py2app 将 .py 打包进 zip，__file__ 指向 zip 内，需要向上找到 Resources/
    exe = Path(sys.executable)
    # 典型路径: dist/AI Guard.app/Contents/MacOS/AI Guard
    # Resources 在: dist/AI Guard.app/Contents/Resources/
    if "Contents/MacOS" in str(exe):
        resources = exe.parent.parent / "Resources"
        bundled = resources / "config.toml"
        if bundled.exists():
            return bundled

    # 3. 兜底：当前工作目录
    cwd_path = Path("config.toml").resolve()
    if cwd_path.exists():
        return cwd_path

    raise FileNotFoundError("config.toml 未找到（开发模式或打包模式均失败）")


BASE_DIR = Path(__file__).parent
config_path = _find_config()
with open(config_path, "rb") as f:
    CFG = tomli.load(f)

SERVER_CFG = CFG.get("server", {})
MONITOR_CFG = CFG.get("monitor", {})
ALERT_CFG = CFG.get("alert", {})
AUTO_KILL_CFG = CFG.get("auto_kill", {})
WHITELIST_CFG = CFG.get("whitelist", {})


# ── 初始化核心组件 ────────────────────────────────────────────
history = MetricsHistory(maxlen=MONITOR_CFG.get("history_points", 150))
alerter = Alerter(ALERT_CFG)
whitelist = WhitelistManager(WHITELIST_CFG)

# 初始化后台线程管理器
threads = BackgroundThreads(CFG, history, alerter, whitelist)

# 初始化运行时配置
threads.settings = {
    "alert": dict(ALERT_CFG),
    "auto_kill": dict(AUTO_KILL_CFG),
    "monitor": {"interval_sec": MONITOR_CFG.get("interval_sec", 15)},
    "scoring": {
        "cpu_caution_pct": 20,
        "idle_min_hours": 1.0,
    },
}


# ── 创建 FastAPI 应用 ─────────────────────────────────────────
# py2app 打包后 BASE_DIR 指向 zip 内，需要找到实际的 Resources 目录
# 用于定位 index.html 等静态资源
def _resolve_base_dir() -> Path:
    """解析正确的 base_dir，支持开发模式和 py2app 打包模式"""
    # 开发模式
    dev_path = Path(__file__).parent
    if (dev_path / "config.toml").exists():
        return dev_path

    # py2app 打包模式
    exe = Path(sys.executable)
    if "Contents/MacOS" in str(exe):
        resources = exe.parent.parent / "Resources"
        if (resources / "config.toml").exists():
            return resources

    return dev_path


RESOLVED_BASE_DIR = _resolve_base_dir()
app = create_app(RESOLVED_BASE_DIR, threads)


@app.on_event("startup")
def on_startup():
    """启动所有后台线程"""
    threads.start_all()

    host = SERVER_CFG.get("host", "127.0.0.1")
    port = SERVER_CFG.get("port", 8765)

    if SERVER_CFG.get("open_browser", True) and not os.environ.get("AIGARD_NO_BROWSER"):
        threading.Timer(1.0, lambda: webbrowser.open(f"http://{host}:{port}")).start()


# ── 启动函数 ──────────────────────────────────────────────────
def start_server(host: str = None, port: int = None):
    """供外部调用的启动函数"""
    _host = host or SERVER_CFG.get("host", "127.0.0.1")
    _port = port or SERVER_CFG.get("port", 8765)
    print(f"AI Guard 服务启动中 → http://{_host}:{_port}")

    # 使用 hypercorn 替代 uvicorn，避免 mypyc 编译模块问题
    config = Config()
    config.bind = [f"{_host}:{_port}"]
    config.loglevel = "WARNING"

    # 在子线程中运行时，禁用信号处理器（避免 RuntimeError）
    import threading
    if threading.current_thread() is not threading.main_thread():
        config.use_reloader = False
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            shutdown_event = asyncio.Event()
            loop.run_until_complete(serve(app, config, shutdown_trigger=shutdown_event.wait))
        finally:
            loop.close()
    else:
        asyncio.run(serve(app, config))


if __name__ == "__main__":
    start_server()
