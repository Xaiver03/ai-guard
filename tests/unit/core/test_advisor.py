"""tests/unit/core/test_advisor.py -- 进程风险评估规则引擎单元测试"""

import time
from unittest.mock import patch, MagicMock
import psutil
from aigard.core.advisor import advise, advise_list, ProcessAdvice


def _proc(**overrides):
    defaults = {
        "pid": 12345,
        "name": "node",
        "cmdline": "/usr/local/bin/node server.js",
        "mem_mb": 350.0,
        "cpu_percent": 5.0,
        "status": "running",
        "create_time": time.time() - 3600,
    }
    defaults.update(overrides)
    return defaults


class TestDangerRule:
    @patch("aigard.core.advisor._count_same_name", return_value=1)
    def test_claude_is_danger(self, _):
        result = advise(_proc(name="claude", cmdline="claude code session"))
        assert result.risk == "danger"
        assert result.action == "leave"

    @patch("aigard.core.advisor._count_same_name", return_value=1)
    def test_terminal_is_danger(self, _):
        result = advise(_proc(name="terminal", cmdline="/usr/bin/terminal"))
        assert result.risk == "danger"

    @patch("aigard.core.advisor._count_same_name", return_value=1)
    def test_docker_is_danger(self, _):
        result = advise(_proc(name="docker", cmdline="docker daemon"))
        assert result.risk == "danger"

    @patch("aigard.core.advisor._count_same_name", return_value=1)
    def test_postgres_is_danger(self, _):
        result = advise(_proc(name="postgres", cmdline="/usr/lib/postgres"))
        assert result.risk == "danger"

    @patch("aigard.core.advisor._count_same_name", return_value=1)
    def test_danger_with_high_cpu(self, _):
        result = advise(_proc(name="claude", cpu_percent=50))
        assert result.risk == "danger"
        assert any("CPU" in r for r in result.reasons)

    @patch("aigard.core.advisor._count_same_name", return_value=1)
    def test_danger_with_low_cpu(self, _):
        result = advise(_proc(name="claude", cpu_percent=2))
        assert result.risk == "danger"


class TestMCPRule:
    @patch("aigard.core.advisor._count_same_name", return_value=1)
    def test_mcp_process_bypasses_danger(self, _):
        result = advise(_proc(
            name="claude",
            cmdline="claude mcp-server-filesystem",
            cpu_percent=2,
        ))
        # MCP should NOT be danger even though "claude" is in name
        assert result.risk != "danger"

    @patch("aigard.core.advisor._count_same_name", return_value=1)
    def test_mcp_open_websearch(self, _):
        result = advise(_proc(
            name="node",
            cmdline="/usr/local/bin/node open-websearch",
            cpu_percent=2,
        ))
        assert result.risk != "danger"
        assert any("MCP" in r for r in result.reasons)


class TestCautionRule:
    @patch("aigard.core.advisor._count_same_name", return_value=1)
    def test_high_cpu_is_caution(self, _):
        result = advise(_proc(name="node", cpu_percent=25))
        assert result.risk == "caution"
        assert result.action == "pause"


class TestSafeRules:
    @patch("aigard.core.advisor._count_same_name", return_value=1)
    def test_lang_server_is_safe(self, _):
        result = advise(_proc(name="pylance", cmdline="pylance-server", mem_mb=500))
        assert result.risk == "safe"
        assert result.action == "kill"

    @patch("aigard.core.advisor._count_same_name", return_value=1)
    def test_lang_server_overrides_cpu_caution(self, _):
        result = advise(_proc(name="pylance", cmdline="pylance-server", cpu_percent=25))
        assert result.risk == "safe"

    @patch("aigard.core.advisor._count_same_name", return_value=1)
    def test_build_tool_is_safe(self, _):
        result = advise(_proc(name="node", cmdline="node webpack --config"))
        assert result.risk == "safe"

    @patch("aigard.core.advisor._count_same_name", return_value=3)
    def test_same_name_count_ge_3(self, _):
        result = advise(_proc(name="node"))
        assert result.risk == "safe"
        assert any("冗余" in r for r in result.reasons)

    @patch("aigard.core.advisor._count_same_name", return_value=1)
    def test_idle_long_running(self, _):
        result = advise(_proc(
            name="node",
            cpu_percent=0.5,
            mem_mb=300,
            create_time=time.time() - 7200,  # 2 hours ago
        ))
        assert result.risk == "safe"
        assert any("空转" in r for r in result.reasons)

    @patch("aigard.core.advisor._count_same_name", return_value=1)
    def test_not_idle_if_short_uptime(self, _):
        result = advise(_proc(
            name="node",
            cpu_percent=0.5,
            mem_mb=300,
            create_time=time.time() - 300,  # 5 minutes, < IDLE_MIN_MINUTES (10)
        ))
        # Should not trigger idle rule
        assert not any("空转" in r for r in result.reasons)


class TestMemoryWarning:
    @patch("aigard.core.advisor._count_same_name", return_value=1)
    def test_high_memory_warning(self, _):
        result = advise(_proc(mem_mb=1200))
        assert any("高内存" in r for r in result.reasons)

    @patch("aigard.core.advisor._count_same_name", return_value=1)
    def test_medium_memory_note(self, _):
        result = advise(_proc(mem_mb=600))
        assert any("中等内存" in r for r in result.reasons)


class TestFallback:
    @patch("aigard.core.advisor._count_same_name", return_value=1)
    def test_generic_process_gets_fallback(self, _):
        result = advise(_proc(
            name="unknown",
            cmdline="unknown-cmd",
            cpu_percent=5,
            mem_mb=50,
            create_time=time.time() - 600,  # 10 min
        ))
        # 默认 risk = "caution"，不满足任何 safe 条件时保持 caution
        assert result.risk == "caution"
        assert any("普通进程" in r for r in result.reasons)


class TestLabels:
    @patch("aigard.core.advisor._count_same_name", return_value=1)
    def test_safe_label(self, _):
        result = advise(_proc(name="unknown", cmdline="webpack"))
        assert "安全终止" in result.label

    @patch("aigard.core.advisor._count_same_name", return_value=1)
    def test_caution_label(self, _):
        result = advise(_proc(name="node", cmdline="node app.js", cpu_percent=25))
        assert "谨慎" in result.label

    @patch("aigard.core.advisor._count_same_name", return_value=1)
    def test_danger_label(self, _):
        result = advise(_proc(name="claude", cmdline="claude"))
        assert "不建议" in result.label


class TestAdviseList:
    @patch("aigard.core.advisor._count_same_name", return_value=1)
    def test_enriches_processes(self, _):
        procs = [_proc(pid=1), _proc(pid=2)]
        result = advise_list(procs)
        assert len(result) == 2
        for r in result:
            assert "risk" in r
            assert "risk_label" in r
            assert "risk_reasons" in r
            assert "suggested_action" in r

    @patch("aigard.core.advisor._count_same_name", return_value=1)
    def test_empty_list(self, _):
        assert advise_list([]) == []


class TestCountSameName:
    """直接测试 _count_same_name 函数"""
    @patch("aigard.core.advisor.psutil.process_iter")
    def test_counts_matching(self, mock_iter):
        from aigard.core.advisor import _count_same_name
        p1 = MagicMock()
        p1.info = {"name": "node"}
        p2 = MagicMock()
        p2.info = {"name": "Node"}  # case insensitive
        p3 = MagicMock()
        p3.info = {"name": "python"}
        mock_iter.return_value = [p1, p2, p3]
        assert _count_same_name("node") == 2

    @patch("aigard.core.advisor.psutil.process_iter")
    def test_handles_access_denied(self, mock_iter):
        from aigard.core.advisor import _count_same_name
        good = MagicMock()
        good.info = {"name": "node"}
        bad = MagicMock()
        type(bad).info = property(lambda self: (_ for _ in ()).throw(psutil.AccessDenied(2)))
        mock_iter.return_value = [good, bad]
        assert _count_same_name("node") == 1

    @patch("aigard.core.advisor.psutil.process_iter")
    def test_handles_none_name(self, mock_iter):
        from aigard.core.advisor import _count_same_name
        p = MagicMock()
        p.info = {"name": None}
        mock_iter.return_value = [p]
        assert _count_same_name("node") == 0
