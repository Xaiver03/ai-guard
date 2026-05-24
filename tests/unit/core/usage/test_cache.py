"""tests/unit/core/usage/test_cache.py -- UsageCache SQLite 单元测试"""

import json
from aigard.core.usage.cache import UsageCache


def _daily_record(date="2026-05-24", input_tokens=1000, output_tokens=500,
                  total_tokens=1800, total_cost=0.01, models=None):
    return {
        "date": date,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cache_creation_tokens": 200,
        "cache_read_tokens": 100,
        "total_tokens": total_tokens,
        "total_cost": total_cost,
        "models_used": models or ["claude-sonnet-4-6"],
        "model_breakdowns": [{"model_name": "claude-sonnet-4-6", "cost": total_cost}],
    }


def _hourly_record(hour="2026-05-24T14", input_tokens=1000, output_tokens=500,
                   total_tokens=1800, total_cost=0.01, models=None):
    return {
        "hour": hour,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cache_creation_tokens": 200,
        "cache_read_tokens": 100,
        "total_tokens": total_tokens,
        "total_cost": total_cost,
        "models_used": models or ["claude-sonnet-4-6"],
    }


class TestInitAndHasData:
    def test_creates_tables(self, tmp_path):
        cache = UsageCache(str(tmp_path))
        assert cache.db_path.exists()

    def test_has_data_empty(self, tmp_path):
        cache = UsageCache(str(tmp_path))
        assert cache.has_data() is False


class TestDailyOperations:
    def test_save_and_get_daily(self, tmp_path):
        cache = UsageCache(str(tmp_path))
        records = [_daily_record("2026-05-24"), _daily_record("2026-05-25")]
        cache.save_daily(records)

        result = cache.get_daily()
        assert len(result) == 2
        assert result[0]["date"] == "2026-05-24"
        assert result[1]["date"] == "2026-05-25"

    def test_get_daily_with_date_range(self, tmp_path):
        cache = UsageCache(str(tmp_path))
        cache.save_daily([
            _daily_record("2026-05-23"),
            _daily_record("2026-05-24"),
            _daily_record("2026-05-25"),
        ])

        result = cache.get_daily("2026-05-24", "2026-05-24")
        assert len(result) == 1
        assert result[0]["date"] == "2026-05-24"

    def test_get_daily_start_only(self, tmp_path):
        cache = UsageCache(str(tmp_path))
        cache.save_daily([
            _daily_record("2026-05-23"),
            _daily_record("2026-05-24"),
            _daily_record("2026-05-25"),
        ])

        result = cache.get_daily(start_date="2026-05-24")
        assert len(result) == 2

    def test_upsert_on_save(self, tmp_path):
        cache = UsageCache(str(tmp_path))
        cache.save_daily([_daily_record("2026-05-24", total_cost=0.01)])
        cache.save_daily([_daily_record("2026-05-24", total_cost=0.05)])

        result = cache.get_daily()
        assert len(result) == 1
        assert result[0]["total_cost"] == 0.05


class TestHourlyOperations:
    def test_save_and_get_hourly(self, tmp_path):
        cache = UsageCache(str(tmp_path))
        cache.save_hourly([
            _hourly_record("2026-05-24T14"),
            _hourly_record("2026-05-24T15"),
        ])

        result = cache.get_hourly()
        assert len(result) == 2
        assert result[0]["hour"] == "2026-05-24T14"

    def test_get_hourly_with_range(self, tmp_path):
        cache = UsageCache(str(tmp_path))
        cache.save_hourly([
            _hourly_record("2026-05-24T13"),
            _hourly_record("2026-05-24T14"),
            _hourly_record("2026-05-24T15"),
        ])

        result = cache.get_hourly("2026-05-24T14", "2026-05-24T14")
        assert len(result) == 1


class TestSummary:
    def test_get_summary_aggregates(self, tmp_path):
        cache = UsageCache(str(tmp_path))
        cache.save_daily([
            _daily_record("2026-05-24", input_tokens=1000, total_cost=0.01),
            _daily_record("2026-05-25", input_tokens=2000, total_cost=0.02),
        ])

        summary = cache.get_summary()
        assert summary["input_tokens"] == 3000
        assert abs(summary["total_cost"] - 0.03) < 1e-4
        assert summary["active_days"] == 2

    def test_get_summary_with_range(self, tmp_path):
        cache = UsageCache(str(tmp_path))
        cache.save_daily([
            _daily_record("2026-05-23", total_cost=0.01),
            _daily_record("2026-05-24", total_cost=0.02),
            _daily_record("2026-05-25", total_cost=0.03),
        ])

        summary = cache.get_summary("2026-05-24", "2026-05-24")
        assert summary["active_days"] == 1
        assert abs(summary["total_cost"] - 0.02) < 1e-4

    def test_count_unique_models(self, tmp_path):
        cache = UsageCache(str(tmp_path))
        cache.save_daily([
            _daily_record("2026-05-24", models=["claude-sonnet-4-6"]),
            _daily_record("2026-05-25", models=["claude-opus-4-6", "claude-sonnet-4-6"]),
        ])

        summary = cache.get_summary()
        assert summary["models_count"] == 2


class TestMetaAndClear:
    def test_set_and_get_last_update_time(self, tmp_path):
        cache = UsageCache(str(tmp_path))
        cache.set_last_update_time("2026-05-24T14:00:00")
        assert cache.get_last_update_time() == "2026-05-24T14:00:00"

    def test_get_last_update_time_empty(self, tmp_path):
        cache = UsageCache(str(tmp_path))
        assert cache.get_last_update_time() is None

    def test_clear(self, tmp_path):
        cache = UsageCache(str(tmp_path))
        cache.save_daily([_daily_record()])
        cache.save_hourly([_hourly_record()])
        cache.set_last_update_time("2026-05-24")

        assert cache.has_data() is True
        cache.clear()
        assert cache.has_data() is False
        assert cache.get_last_update_time() is None
