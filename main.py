"""
AI Guard - 智能内存守护
主入口文件
"""

import os
import threading
import webbrowser
from pathlib import Path

import tomli
import uvicorn

from aigard.core import MetricsHistory, Alerter
from aigard.core.threads import BackgroundThreads
from aigard.api import create_app


# ── 配置加载 ──────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
# py2app 打包后 config.toml 在 Resources/ 目录下
config_path = BASE_DIR / "config.toml"
if not config_path.exists():
    config_path = BASE_DIR.parent / "config.toml"
with open(config_path, "rb") as f:
    CFG = tomli.load(f)

SERVER_CFG = CFG.get("server", {})
MONITOR_CFG = CFG.get("monitor", {})
ALERT_CFG = CFG.get("alert", {})
AUTO_KILL_CFG = CFG.get("auto_kill", {})


# ── 初始化核心组件 ────────────────────────────────────────────
history = MetricsHistory(maxlen=MONITOR_CFG.get("history_points", 150))
alerter = Alerter(ALERT_CFG)

# 初始化后台线程管理器
threads = BackgroundThreads(CFG, history, alerter)

# 初始化运行时配置
threads.settings = {
    "alert": dict(ALERT_CFG),
    "auto_kill": dict(AUTO_KILL_CFG),
    "monitor": {"interval_sec": MONITOR_CFG.get("interval_sec", 1)},
    "scoring": {
        "cpu_caution_pct": 20,
        "idle_min_hours": 1.0,
    },
}


# ── 创建 FastAPI 应用 ─────────────────────────────────────────
app = create_app(BASE_DIR, threads)


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
    uvicorn.run(app, host=_host, port=_port, log_level="warning")


if __name__ == "__main__":
    start_server()
