"""
AI Guard - Intelligent Memory Guardian
Main entry file
"""

import os
import sys
import threading
import webbrowser
from pathlib import Path

import tomllib
import asyncio
from hypercorn.config import Config
from hypercorn.asyncio import serve

from aigard.core import MetricsHistory, Alerter, WhitelistManager
from aigard.core.threads import BackgroundThreads
from aigard.api import create_app
from aigard.updater import CURRENT_VERSION

# Export VERSION for app_native.py
VERSION = CURRENT_VERSION


# ── Configuration Loading ──────────────────────────────────────
def _find_config() -> Path:
    """Find config.toml, support dev mode and py2app packaging mode"""
    # 1. Dev mode: same level as main.py
    dev_path = Path(__file__).parent / "config.toml"
    if dev_path.exists():
        return dev_path

    # 2. py2app packaging mode: Resources/ directory
    # py2app packages .py into zip, __file__ points to zip, need to find Resources/
    exe = Path(sys.executable)
    # Typical path: dist/AI Guard.app/Contents/MacOS/AI Guard
    # Resources at: dist/AI Guard.app/Contents/Resources/
    if "Contents/MacOS" in str(exe):
        resources = exe.parent.parent / "Resources"
        bundled = resources / "config.toml"
        if bundled.exists():
            return bundled

    # 3. Fallback: current working directory
    cwd_path = Path("config.toml").resolve()
    if cwd_path.exists():
        return cwd_path

    raise FileNotFoundError("config.toml not found (both dev mode and packaging mode failed)")


BASE_DIR = Path(__file__).parent
config_path = _find_config()
with open(config_path, "rb") as f:
    CFG = tomllib.load(f)

SERVER_CFG = CFG.get("server", {})
MONITOR_CFG = CFG.get("monitor", {})
ALERT_CFG = CFG.get("alert", {})
AUTO_KILL_CFG = CFG.get("auto_kill", {})
WHITELIST_CFG = CFG.get("whitelist", {})


# ── Initialize Core Components ────────────────────────────────
history = MetricsHistory(maxlen=MONITOR_CFG.get("history_points", 150))
alerter = Alerter(ALERT_CFG)
whitelist = WhitelistManager(WHITELIST_CFG)

# Initialize background thread manager
threads = BackgroundThreads(CFG, history, alerter, whitelist)

# Initialize runtime configuration
PROCESSES_CFG = CFG.get("processes", {})
SCORING_CFG = PROCESSES_CFG.get("scoring", {})

threads.settings = {
    "alert": dict(ALERT_CFG),
    "auto_kill": dict(AUTO_KILL_CFG),
    "monitor": {"interval_sec": MONITOR_CFG.get("interval_sec", 15)},
    "scoring": {
        "cpu_caution_pct": SCORING_CFG.get("cpu_caution_pct", 20),
        "idle_min_minutes": SCORING_CFG.get("idle_min_minutes", 10),
    },
}


# ── Create FastAPI Application ─────────────────────────────────
# After py2app packaging, BASE_DIR points to zip, need to find actual Resources directory
# Used to locate static resources like index.html
def _resolve_base_dir() -> Path:
    """Parse correct base_dir, support dev mode and py2app packaging mode"""
    # py2app packaging mode - 优先检查
    if getattr(sys, 'frozen', False):
        exe = Path(sys.executable)
        if "Contents/MacOS" in str(exe):
            resources = exe.parent.parent / "Resources"
            if (resources / "config.toml").exists():
                return resources

    # Dev mode
    dev_path = Path(__file__).parent
    if (dev_path / "config.toml").exists():
        return dev_path

    return dev_path


RESOLVED_BASE_DIR = _resolve_base_dir()
app = create_app(RESOLVED_BASE_DIR, threads)


@app.on_event("startup")
def on_startup():
    """Start all background threads"""
    threads.start_all()

    host = SERVER_CFG.get("host", "127.0.0.1")
    port = SERVER_CFG.get("port", 8765)

    if SERVER_CFG.get("open_browser", True) and not os.environ.get("AIGARD_NO_BROWSER"):
        threading.Timer(1.0, lambda: webbrowser.open(f"http://{host}:{port}")).start()


# ── Startup Function ──────────────────────────────────────────
def start_server(host: str | None = None, port: int | None = None):
    """Startup function for external calls."""
    import time

    _host = host or SERVER_CFG.get("host", "127.0.0.1")
    _port = port or SERVER_CFG.get("port", 8765)
    print(f"AI Guard service starting → http://{_host}:{_port}")

    # Use hypercorn instead of uvicorn to avoid mypyc compiled module issues
    config = Config()
    config.bind = [f"{_host}:{_port}"]
    config.loglevel = "WARNING"

    # Check if running in subthread (from app_native.py)
    is_subthread = threading.current_thread() is not threading.main_thread()

    if is_subthread:
        config.use_reloader = False
        # Run in a dedicated event loop in subthread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            shutdown_event = asyncio.Event()
            loop.run_until_complete(serve(app, config, shutdown_trigger=shutdown_event.wait))  # type: ignore[arg-type]
        except OSError as e:
            if e.errno == 48:  # Address already in use
                print(f"[ERROR] Port {_port} is already in use. Another instance may be running.")
                print(f"[ERROR] Please quit the other AI Guard instance or wait a few seconds.")
            else:
                print(f"[ERROR] Server failed to start: {e}")
            raise
        finally:
            try:
                loop.close()
            except Exception:
                pass
    else:
        asyncio.run(serve(app, config))  # type: ignore[arg-type]


if __name__ == "__main__":
    start_server()
