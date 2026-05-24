"""Unit-test specific fixtures -- mocks for psutil, os.kill, etc."""

from unittest.mock import MagicMock
import pytest


@pytest.fixture
def mock_psutil_virtual_memory():
    mem = MagicMock()
    mem.total = 16 * (1024 ** 3)
    mem.used = 10 * (1024 ** 3)
    mem.available = 6 * (1024 ** 3)
    mem.percent = 62.5
    return mem


@pytest.fixture
def mock_psutil_swap_memory():
    swap = MagicMock()
    swap.total = 4 * (1024 ** 3)
    swap.used = 1 * (1024 ** 3)
    swap.percent = 25.0
    return swap


@pytest.fixture
def mock_psutil_disk_usage():
    disk = MagicMock()
    disk.total = 500 * (1024 ** 3)
    disk.used = 250 * (1024 ** 3)
    disk.free = 250 * (1024 ** 3)
    disk.percent = 50.0
    return disk


@pytest.fixture
def make_fake_process():
    """Build fake process info dicts for psutil.process_iter mocking."""
    def _build(process_list):
        mocks = []
        for p in process_list:
            mem_info = MagicMock()
            mem_info.rss = p.get("memory_info_rss", 100 * 1024 * 1024)
            proc = MagicMock()
            proc.info = {
                "pid": p["pid"],
                "name": p.get("name", "test"),
                "cmdline": p.get("cmdline", ["/usr/bin/test"]),
                "memory_info": mem_info,
                "cpu_percent": p.get("cpu_percent", 0.0),
                "status": p.get("status", "running"),
                "create_time": p.get("create_time", 1000000.0),
            }
            mocks.append(proc)
        return mocks
    return _build
