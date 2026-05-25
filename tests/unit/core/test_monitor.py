"""tests/unit/core/test_monitor.py -- 系统指标采集单元测试"""

import time
from unittest.mock import patch, MagicMock
from aigard.core.monitor import (
    _gb, collect_metrics, collect_ai_processes, collect_all_processes,
    MetricsHistory, Metrics, ProcessInfo,
)
import psutil


class TestGbConversion:
    def test_one_gb(self):
        assert _gb(1024 ** 3) == 1.0

    def test_zero(self):
        assert _gb(0) == 0.0

    def test_fractional(self):
        assert _gb(512 * 1024 * 1024) == 0.5


class TestCollectMetrics:
    @patch("aigard.core.monitor.psutil.cpu_percent", return_value=25.0)
    @patch("aigard.core.monitor.psutil.disk_usage")
    @patch("aigard.core.monitor.psutil.swap_memory")
    @patch("aigard.core.monitor.psutil.virtual_memory")
    def test_returns_valid_metrics(self, mock_mem, mock_swap, mock_disk, mock_cpu):
        mock_mem.return_value = MagicMock(
            total=16 * 1024**3, used=10 * 1024**3,
            available=6 * 1024**3, percent=62.5
        )
        mock_swap.return_value = MagicMock(
            total=4 * 1024**3, used=1 * 1024**3, percent=25.0
        )
        mock_disk.return_value = MagicMock(
            total=500 * 1024**3, used=250 * 1024**3,
            free=250 * 1024**3, percent=50.0
        )

        m = collect_metrics()
        assert isinstance(m, Metrics)
        assert m.mem_total_gb == 16.0
        assert m.mem_used_gb == 10.0
        assert m.mem_percent == 62.5
        assert m.swap_percent == 25.0
        assert m.disk_free_gb == 250.0
        assert m.cpu_percent == 25.0

    @patch("aigard.core.monitor.psutil.cpu_percent")
    @patch("aigard.core.monitor.psutil.disk_usage")
    @patch("aigard.core.monitor.psutil.swap_memory")
    @patch("aigard.core.monitor.psutil.virtual_memory")
    def test_cpu_zero_interval(self, mock_mem, mock_swap, mock_disk, mock_cpu):
        mock_mem.return_value = MagicMock(total=1, used=0, available=1, percent=0)
        mock_swap.return_value = MagicMock(total=1, used=0, percent=0)
        mock_disk.return_value = MagicMock(total=1, used=0, free=1, percent=0)
        mock_cpu.return_value = 0.0
        collect_metrics()
        mock_cpu.assert_called_once_with(interval=0)


class TestCollectAiProcesses:
    @patch("aigard.core.monitor.psutil.process_iter")
    def test_filters_by_keyword(self, mock_iter):
        mem = MagicMock()
        mem.rss = 200 * 1024 * 1024
        p1 = MagicMock()
        p1.info = {"pid": 1, "name": "claude", "cmdline": ["claude"], "memory_info": mem,
                    "cpu_percent": 5.0, "status": "running", "create_time": 1000.0}
        p2 = MagicMock()
        p2.info = {"pid": 2, "name": "chrome", "cmdline": ["chrome"], "memory_info": mem,
                    "cpu_percent": 3.0, "status": "running", "create_time": 1000.0}
        mock_iter.return_value = [p1, p2]

        result = collect_ai_processes(["claude"])
        assert len(result) == 1
        assert result[0].name == "claude"

    @patch("aigard.core.monitor.psutil.process_iter")
    def test_case_insensitive(self, mock_iter):
        mem = MagicMock()
        mem.rss = 100 * 1024 * 1024
        p = MagicMock()
        p.info = {"pid": 1, "name": "Claude", "cmdline": ["Claude"], "memory_info": mem,
                  "cpu_percent": 0.0, "status": "running", "create_time": 1000.0}
        mock_iter.return_value = [p]
        result = collect_ai_processes(["claude"])
        assert len(result) == 1

    @patch("aigard.core.monitor.psutil.process_iter")
    def test_matches_cmdline(self, mock_iter):
        mem = MagicMock()
        mem.rss = 100 * 1024 * 1024
        p = MagicMock()
        p.info = {"pid": 1, "name": "node", "cmdline": ["node", "claude-mcp"], "memory_info": mem,
                  "cpu_percent": 0.0, "status": "running", "create_time": 1000.0}
        mock_iter.return_value = [p]
        result = collect_ai_processes(["claude"])
        assert len(result) == 1

    @patch("aigard.core.monitor.psutil.process_iter")
    def test_sorted_by_mem_desc(self, mock_iter):
        def make_proc(pid, name, rss_mb):
            mem = MagicMock()
            mem.rss = rss_mb * 1024 * 1024
            p = MagicMock()
            p.info = {"pid": pid, "name": name, "cmdline": [name], "memory_info": mem,
                      "cpu_percent": 0.0, "status": "running", "create_time": 1000.0}
            return p

        mock_iter.return_value = [
            make_proc(1, "node", 100),
            make_proc(2, "node", 500),
            make_proc(3, "node", 300),
        ]
        result = collect_ai_processes(["node"])
        assert result[0].mem_mb == 500.0
        assert result[1].mem_mb == 300.0
        assert result[2].mem_mb == 100.0

    @patch("aigard.core.monitor.psutil.process_iter")
    def test_handles_no_such_process(self, mock_iter):
        bad = MagicMock()
        bad.info.__getitem__ = MagicMock(side_effect=psutil.NoSuchProcess(1))
        # Force the 'info' dict access to raise
        type(bad).info = property(lambda self: (_ for _ in ()).throw(psutil.NoSuchProcess(1)))
        mock_iter.return_value = [bad]
        result = collect_ai_processes(["test"])
        assert result == []

    @patch("aigard.core.monitor.psutil.process_iter")
    def test_empty_keywords(self, mock_iter):
        mock_iter.return_value = []
        result = collect_ai_processes([])
        assert result == []


class TestMetricsHistory:
    def test_push_and_get_all(self, make_metrics):
        h = MetricsHistory(maxlen=10)
        m1 = make_metrics(cpu_percent=10)
        m2 = make_metrics(cpu_percent=20)
        h.push(m1)
        h.push(m2)
        all_data = h.get_all()
        assert len(all_data) == 2
        assert all_data[0]["cpu_percent"] == 10
        assert all_data[1]["cpu_percent"] == 20

    def test_maxlen_eviction(self, make_metrics):
        h = MetricsHistory(maxlen=2)
        h.push(make_metrics(cpu_percent=10))
        h.push(make_metrics(cpu_percent=20))
        h.push(make_metrics(cpu_percent=30))
        all_data = h.get_all()
        assert len(all_data) == 2
        assert all_data[0]["cpu_percent"] == 20

    def test_latest_empty(self):
        h = MetricsHistory()
        assert h.latest is None

    def test_latest_returns_last(self, make_metrics):
        h = MetricsHistory()
        h.push(make_metrics(cpu_percent=10))
        h.push(make_metrics(cpu_percent=20))
        assert h.latest["cpu_percent"] == 20

    def test_to_dict(self, make_metrics):
        m = make_metrics()
        d = m.to_dict()
        assert isinstance(d, dict)
        assert "mem_percent" in d
        assert "cpu_percent" in d


class TestCollectAllProcesses:
    @patch("aigard.core.monitor.psutil.process_iter")
    def test_returns_sorted_by_mem(self, mock_iter):
        def make(pid, name, rss_mb):
            p = MagicMock()
            mem = MagicMock()
            mem.rss = rss_mb * 1024 * 1024
            p.info = {"pid": pid, "name": name, "cmdline": [name],
                      "memory_info": mem, "cpu_percent": 1.0,
                      "status": "running", "create_time": 1000.0}
            return p

        mock_iter.return_value = [make(1, "a", 50), make(2, "b", 200), make(3, "c", 100)]
        result = collect_all_processes()
        assert len(result) == 3
        assert result[0].mem_mb == 200.0
        assert result[1].mem_mb == 100.0
        assert result[2].mem_mb == 50.0

    @patch("aigard.core.monitor.psutil.process_iter")
    def test_skips_access_denied(self, mock_iter):
        good = MagicMock()
        mem = MagicMock()
        mem.rss = 100 * 1024 * 1024
        good.info = {"pid": 1, "name": "ok", "cmdline": ["ok"],
                     "memory_info": mem, "cpu_percent": 0.0,
                     "status": "running", "create_time": 1000.0}
        bad = MagicMock()
        type(bad).info = property(lambda self: (_ for _ in ()).throw(psutil.AccessDenied(2)))
        mock_iter.return_value = [good, bad]
        result = collect_all_processes()
        assert len(result) == 1

    @patch("aigard.core.monitor.psutil.process_iter")
    def test_handles_none_memory_info(self, mock_iter):
        p = MagicMock()
        p.info = {"pid": 1, "name": "test", "cmdline": None,
                  "memory_info": None, "cpu_percent": None,
                  "status": None, "create_time": None}
        mock_iter.return_value = [p]
        result = collect_all_processes()
        assert len(result) == 1
        assert result[0].mem_mb == 0.0
        assert result[0].cmdline == ""
        assert result[0].cpu_percent == 0.0
