"""tests/unit/core/test_killer.py -- 进程干预操作单元测试"""

import signal
from unittest.mock import patch, MagicMock, PropertyMock
import psutil
from aigard.core.killer import pause_process, resume_process, kill_process, ActionResult


class TestPauseProcess:
    @patch("aigard.core.killer.os.kill")
    @patch("aigard.core.killer._get_proc")
    def test_success(self, mock_get, mock_kill):
        proc = MagicMock()
        proc.memory_info.return_value.rss = 200 * 1024 * 1024
        proc.name.return_value = "test"
        mock_get.return_value = proc

        result = pause_process(123)
        assert result.success is True
        mock_kill.assert_called_once_with(123, signal.SIGSTOP)

    @patch("aigard.core.killer._get_proc")
    def test_not_found(self, mock_get):
        mock_get.return_value = None
        result = pause_process(999)
        assert result.success is False
        assert "不存在" in result.message

    @patch("aigard.core.killer.os.kill", side_effect=PermissionError())
    @patch("aigard.core.killer._get_proc")
    def test_permission_error(self, mock_get, mock_kill):
        proc = MagicMock()
        proc.memory_info.return_value.rss = 100 * 1024 * 1024
        proc.name.return_value = "test"
        mock_get.return_value = proc

        result = pause_process(123)
        assert result.success is False
        assert "权限" in result.message


class TestResumeProcess:
    @patch("aigard.core.killer.os.kill")
    @patch("aigard.core.killer._get_proc")
    def test_success(self, mock_get, mock_kill):
        proc = MagicMock()
        proc.name.return_value = "test"
        mock_get.return_value = proc

        result = resume_process(123)
        assert result.success is True
        mock_kill.assert_called_once_with(123, signal.SIGCONT)

    @patch("aigard.core.killer._get_proc")
    def test_not_found(self, mock_get):
        mock_get.return_value = None
        result = resume_process(999)
        assert result.success is False


class TestKillProcess:
    @patch("aigard.core.killer.os.kill")
    @patch("aigard.core.killer._get_proc")
    def test_success(self, mock_get, mock_kill):
        proc = MagicMock()
        proc.name.return_value = "test"
        proc.memory_info.return_value.rss = 300 * 1024 * 1024
        proc.status.return_value = "running"
        mock_get.return_value = proc

        result = kill_process(123)
        assert result.success is True
        assert result.mem_freed_mb > 0
        proc.terminate.assert_called_once()
        # os.kill should NOT be called for SIGCONT since status is "running"
        mock_kill.assert_not_called()

    @patch("aigard.core.killer._get_proc")
    def test_not_found(self, mock_get):
        mock_get.return_value = None
        result = kill_process(999)
        assert result.success is False

    @patch("aigard.core.killer.os.kill")
    @patch("aigard.core.killer._get_proc")
    def test_resumes_stopped_before_kill(self, mock_get, mock_kill):
        proc = MagicMock()
        proc.name.return_value = "test"
        proc.memory_info.return_value.rss = 100 * 1024 * 1024
        proc.status.return_value = psutil.STATUS_STOPPED
        mock_get.return_value = proc

        result = kill_process(123)
        assert result.success is True
        mock_kill.assert_called_once_with(123, signal.SIGCONT)
        proc.terminate.assert_called_once()

    @patch("aigard.core.killer._get_proc")
    def test_permission_error(self, mock_get):
        proc = MagicMock()
        proc.name.return_value = "test"
        proc.memory_info.return_value.rss = 100 * 1024 * 1024
        proc.status.return_value = "running"
        proc.terminate.side_effect = PermissionError()
        mock_get.return_value = proc

        result = kill_process(123)
        assert result.success is False
        assert "权限" in result.message
