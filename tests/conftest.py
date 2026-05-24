"""Root conftest.py -- fixtures usable by all tests."""

import time
import pytest
from datetime import datetime
from aigard.core.monitor import Metrics, ProcessInfo, MetricsHistory
from aigard.core.usage.models import UsageEntry


@pytest.fixture
def make_metrics():
    """Factory fixture: returns a callable that produces Metrics with overrides."""
    def _make(**overrides):
        defaults = dict(
            ts=time.time(),
            mem_total_gb=16.0,
            mem_used_gb=8.0,
            mem_percent=50.0,
            mem_available_gb=8.0,
            swap_total_gb=4.0,
            swap_used_gb=0.5,
            swap_percent=12.5,
            disk_total_gb=500.0,
            disk_used_gb=250.0,
            disk_free_gb=250.0,
            disk_percent=50.0,
            cpu_percent=15.0,
            alert_level="normal",
        )
        defaults.update(overrides)
        return Metrics(**defaults)
    return _make


@pytest.fixture
def sample_process_info():
    """Returns a dict matching what monitor.collect_ai_processes returns (after conversion)."""
    return {
        "pid": 12345,
        "name": "node",
        "cmdline": "/usr/local/bin/node server.js",
        "mem_mb": 350.0,
        "cpu_percent": 5.0,
        "status": "running",
        "create_time": time.time() - 7200,
    }


@pytest.fixture
def make_usage_entry():
    """Factory for UsageEntry instances."""
    def _make(**overrides):
        defaults = dict(
            timestamp=datetime(2026, 5, 24, 14, 30, 0),
            model="claude-sonnet-4-6",
            input_tokens=1000,
            output_tokens=500,
            cache_creation_tokens=200,
            cache_read_tokens=100,
            cost=0.0,
            project="test-project",
            session_id="abc123",
        )
        defaults.update(overrides)
        return UsageEntry(**defaults)
    return _make


@pytest.fixture
def sample_config():
    """A minimal config dict matching config.toml structure."""
    return {
        "server": {"host": "127.0.0.1", "port": 8765, "open_browser": False},
        "monitor": {"interval_sec": 1, "history_points": 150},
        "alert": {
            "mem_warn": 80, "mem_crit": 90,
            "swap_warn": 50, "swap_crit": 80,
            "disk_free_warn_gb": 20, "disk_free_crit_gb": 10,
            "cooldown_sec": 60, "swap_cooldown_sec": 300,
        },
        "auto_kill": {
            "enabled": False, "mem_trigger_pct": 85,
            "swap_trigger_pct": 75, "target_mem_pct": 70, "cooldown_sec": 120,
        },
        "processes": {"watch_keywords": ["claude", "node", "python"]},
        "whitelist": {"process_names": [], "command_keywords": [], "pids": []},
        "usage": {"claude_data_dir": "~/.claude", "cache_ttl": 300},
    }
