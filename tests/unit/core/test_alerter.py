"""tests/unit/core/test_alerter.py -- Alerter 单元测试"""

import time
from unittest.mock import patch, MagicMock
from aigard.core.alerter import Alerter


def _make_alerter(**overrides):
    cfg = {
        "mem_warn": 80, "mem_crit": 90,
        "swap_warn": 50, "swap_crit": 80,
        "disk_free_warn_gb": 20, "disk_free_crit_gb": 10,
        "cooldown_sec": 60, "swap_cooldown_sec": 300,
    }
    cfg.update(overrides)
    return Alerter(cfg)


def _metrics(**overrides):
    defaults = {"mem_percent": 50, "swap_percent": 10, "disk_free_gb": 100}
    defaults.update(overrides)
    return defaults


class TestCheckLevel:
    @patch.object(Alerter, '_notify')
    def test_normal_when_all_ok(self, mock_notify):
        a = _make_alerter()
        level = a.check(_metrics())
        assert level == "normal"
        mock_notify.assert_not_called()

    @patch.object(Alerter, '_notify')
    def test_warn_on_mem_warn(self, mock_notify):
        a = _make_alerter()
        level = a.check(_metrics(mem_percent=82))
        assert level == "warn"

    @patch.object(Alerter, '_notify')
    def test_crit_on_mem_crit(self, mock_notify):
        a = _make_alerter()
        level = a.check(_metrics(mem_percent=92))
        assert level == "crit"

    @patch.object(Alerter, '_notify')
    def test_warn_on_swap_warn(self, mock_notify):
        a = _make_alerter()
        level = a.check(_metrics(swap_percent=55))
        assert level == "warn"

    @patch.object(Alerter, '_notify')
    def test_crit_on_swap_crit(self, mock_notify):
        a = _make_alerter()
        level = a.check(_metrics(swap_percent=85))
        assert level == "crit"

    @patch.object(Alerter, '_notify')
    def test_warn_on_low_disk(self, mock_notify):
        a = _make_alerter()
        level = a.check(_metrics(disk_free_gb=15))
        assert level == "warn"

    @patch.object(Alerter, '_notify')
    def test_crit_on_very_low_disk(self, mock_notify):
        a = _make_alerter()
        level = a.check(_metrics(disk_free_gb=5))
        assert level == "crit"

    @patch.object(Alerter, '_notify')
    def test_crit_overrides_warn(self, mock_notify):
        a = _make_alerter()
        level = a.check(_metrics(mem_percent=82, swap_percent=85))
        assert level == "crit"


class TestCooldown:
    @patch.object(Alerter, '_notify')
    def test_cooldown_prevents_duplicate(self, mock_notify):
        a = _make_alerter()
        a.check(_metrics(mem_percent=92))
        a.check(_metrics(mem_percent=92))
        assert mock_notify.call_count == 1

    @patch.object(Alerter, '_notify')
    @patch('aigard.core.alerter.time.time')
    def test_cooldown_expires_allows_new(self, mock_time, mock_notify):
        a = _make_alerter()
        mock_time.return_value = 1000.0
        a.check(_metrics(mem_percent=92))
        assert mock_notify.call_count == 1

        mock_time.return_value = 1061.0  # 61s later > cooldown_sec(60)
        a.check(_metrics(mem_percent=92))
        assert mock_notify.call_count == 2


class TestSwapSuppression:
    @patch.object(Alerter, '_notify')
    @patch('aigard.core.alerter.time.time')
    def test_suppress_swap_alert(self, mock_time, mock_notify):
        a = _make_alerter()
        mock_time.return_value = 1000.0
        a.suppress_swap_alert(180)

        level = a.check(_metrics(swap_percent=85))
        # swap_crit is suppressed, but mem is fine -> normal
        assert level == "normal"

    @patch.object(Alerter, '_notify')
    @patch('aigard.core.alerter.time.time')
    def test_suppress_expires(self, mock_time, mock_notify):
        a = _make_alerter()
        mock_time.return_value = 1000.0
        a.suppress_swap_alert(180)

        mock_time.return_value = 1181.0  # 181s later, suppression expired
        level = a.check(_metrics(swap_percent=85))
        assert level == "crit"

    @patch.object(Alerter, '_notify')
    @patch('aigard.core.alerter.time.time')
    def test_suppress_swap_mem_still_triggers(self, mock_time, mock_notify):
        a = _make_alerter()
        mock_time.return_value = 1000.0
        a.suppress_swap_alert(180)

        # Swap suppressed, but mem_crit still triggers
        level = a.check(_metrics(mem_percent=92, swap_percent=85))
        assert level == "crit"


class TestNotify:
    def test_notify_uses_rumps_when_available(self):
        a = _make_alerter()
        mock_rumps = MagicMock()
        with patch.dict('sys.modules', {'rumps': mock_rumps}):
            a._notify("title", "body")
            mock_rumps.notification.assert_called_once()

    def test_notify_falls_back_to_osascript(self):
        a = _make_alerter()
        # Remove rumps from sys.modules so import raises ImportError
        with patch.dict('sys.modules', {'rumps': None}):
            with patch('aigard.core.alerter.subprocess.run') as mock_run:
                a._notify("title", "body")
                mock_run.assert_called_once()

    def test_notify_handles_all_failures(self):
        a = _make_alerter()
        with patch.dict('sys.modules', {'rumps': None}):
            with patch('aigard.core.alerter.subprocess.run', side_effect=Exception("fail")):
                # Should not raise
                a._notify("title", "body")
