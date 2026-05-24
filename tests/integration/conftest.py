"""Integration test conftest -- provides a fully wired FastAPI TestClient
without importing main.py's top-level code.

Strategy:
1. Create our own instances of MetricsHistory, Alerter, WhitelistManager
2. Build a mock BackgroundThreads with the same shared state interface
3. Inject a fake `main` module into sys.modules["main"] so that
   `import main as _main_mod` inside route handlers resolves correctly
4. Call create_app(base_dir, threads_manager) to get a clean FastAPI app
5. Do NOT start background threads -- we just test API request/response
"""

import sys
import types
import threading
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from aigard.core.monitor import MetricsHistory
from aigard.core.alerter import Alerter
from aigard.core.whitelist import WhitelistManager


@pytest.fixture
def integration_app(tmp_path, sample_config):
    """Create a FastAPI app backed by test-safe instances with fake main module."""
    # Build real instances with test config
    history = MetricsHistory(maxlen=150)
    alerter = Alerter(sample_config["alert"])
    whitelist = WhitelistManager(sample_config["whitelist"])

    # Build a lightweight threads_manager mock
    threads_manager = MagicMock()
    threads_manager.history = history
    threads_manager.alerter = alerter
    threads_manager.whitelist = whitelist
    threads_manager.latest_processes = []
    threads_manager.auto_kill_log = []
    threads_manager.autokill_enabled = False
    threads_manager.blocked_processes = set()
    threads_manager.scheduled_kill_enabled = False
    threads_manager.scheduled_kill_interval = 10
    threads_manager.settings = {
        "alert": dict(sample_config["alert"]),
        "auto_kill": dict(sample_config["auto_kill"]),
        "monitor": {"interval_sec": 1},
        "scoring": {"cpu_caution_pct": 20, "idle_min_hours": 1.0},
    }
    threads_manager.config = sample_config
    # Use real Lock objects so `with threads_manager.lock:` works
    threads_manager.lock = threading.Lock()
    threads_manager.settings_lock = threading.Lock()

    # Create UI files for HTML serving tests
    ui_dir = tmp_path / "aigard" / "ui"
    ui_dir.mkdir(parents=True)
    (ui_dir / "index.html").write_text("<html>index</html>")
    (ui_dir / "bookmarks.html").write_text("<html>bookmarks</html>")
    (ui_dir / "usage.html").write_text("<html>usage</html>")

    # Fake `main` module
    fake_main = types.ModuleType("main")
    fake_main.CFG = sample_config
    fake_main.whitelist = whitelist
    fake_main.history = history
    fake_main.alerter = alerter
    fake_main.threads = threads_manager

    # Write a temporary config.toml
    config_toml_path = tmp_path / "config.toml"
    config_toml_path.write_text("")

    old_main = sys.modules.get("main")
    sys.modules["main"] = fake_main

    try:
        from aigard.api.routes import create_app
        app = create_app(tmp_path, threads_manager)
        yield app, threads_manager, whitelist, history, alerter
    finally:
        if old_main is not None:
            sys.modules["main"] = old_main
        else:
            sys.modules.pop("main", None)


@pytest.fixture
def client(integration_app):
    """Synchronous FastAPI TestClient for integration tests."""
    app, *_ = integration_app
    with TestClient(app) as c:
        yield c


@pytest.fixture
def app_state(integration_app):
    """Provides access to the underlying test objects for assertions."""
    app, threads_manager, whitelist, history, alerter = integration_app
    return {
        "app": app,
        "threads": threads_manager,
        "whitelist": whitelist,
        "history": history,
        "alerter": alerter,
    }
