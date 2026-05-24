"""tests/unit/test_alert_history.py -- 告警历史 SQLite 单元测试"""

from unittest.mock import patch
from pathlib import Path
import alert_history


class TestAlertHistory:
    def test_record_and_get_recent(self, tmp_path):
        db_path = tmp_path / "test_alerts.db"
        with patch.object(alert_history, "DB_PATH", db_path):
            alert_history.record_alert("warn", "内存 82%")
            alert_history.record_alert("crit", "内存 92%")
            alert_history.record_alert("warn", "Swap 55%")

            result = alert_history.get_recent_alerts(20)
            assert len(result) == 3
            # Ordered by ts DESC
            assert result[0]["reason"] == "Swap 55%"
            assert result[2]["reason"] == "内存 82%"

    def test_record_ignores_normal(self, tmp_path):
        db_path = tmp_path / "test_alerts.db"
        with patch.object(alert_history, "DB_PATH", db_path):
            alert_history.record_alert("normal", "一切正常")
            result = alert_history.get_recent_alerts(20)
            assert len(result) == 0

    def test_record_only_warn_and_crit(self, tmp_path):
        db_path = tmp_path / "test_alerts.db"
        with patch.object(alert_history, "DB_PATH", db_path):
            alert_history.record_alert("info", "信息")
            alert_history.record_alert("warn", "警告")
            alert_history.record_alert("crit", "危险")
            result = alert_history.get_recent_alerts(20)
            assert len(result) == 2

    def test_get_recent_limit(self, tmp_path):
        db_path = tmp_path / "test_alerts.db"
        with patch.object(alert_history, "DB_PATH", db_path):
            for i in range(5):
                alert_history.record_alert("warn", f"告警 {i}")
            result = alert_history.get_recent_alerts(2)
            assert len(result) == 2

    def test_get_recent_empty_db(self, tmp_path):
        db_path = tmp_path / "test_alerts.db"
        with patch.object(alert_history, "DB_PATH", db_path):
            result = alert_history.get_recent_alerts(20)
            assert result == []
