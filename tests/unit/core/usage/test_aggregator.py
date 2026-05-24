"""tests/unit/core/usage/test_aggregator.py -- UsageAggregator 单元测试"""

from datetime import datetime
from aigard.core.usage.aggregator import UsageAggregator
from aigard.core.usage.calculator import UsageCalculator
from aigard.core.usage.pricing import PricingManager
from aigard.core.usage.models import UsageEntry


def _entry(**overrides):
    defaults = dict(
        timestamp=datetime(2026, 5, 24, 14, 30),
        model="claude-sonnet-4-6",
        input_tokens=1000,
        output_tokens=500,
        cache_creation_tokens=200,
        cache_read_tokens=100,
        cost=0.0,
        project="test",
        session_id="s1",
    )
    defaults.update(overrides)
    return UsageEntry(**defaults)


def _make_aggregator():
    pm = PricingManager()
    calc = UsageCalculator(pm)
    return UsageAggregator(calc)


class TestAggregateByHour:
    def test_same_hour_grouped(self):
        agg = _make_aggregator()
        entries = [
            _entry(timestamp=datetime(2026, 5, 24, 14, 0)),
            _entry(timestamp=datetime(2026, 5, 24, 14, 30)),
        ]
        result = agg.aggregate_by_hour(entries)
        assert len(result) == 1
        assert result[0].hour == "2026-05-24T14"
        assert result[0].input_tokens == 2000

    def test_different_hours_separated(self):
        agg = _make_aggregator()
        entries = [
            _entry(timestamp=datetime(2026, 5, 24, 14, 0)),
            _entry(timestamp=datetime(2026, 5, 24, 15, 0)),
        ]
        result = agg.aggregate_by_hour(entries)
        assert len(result) == 2

    def test_sorted_chronologically(self):
        agg = _make_aggregator()
        entries = [
            _entry(timestamp=datetime(2026, 5, 24, 16, 0)),
            _entry(timestamp=datetime(2026, 5, 24, 14, 0)),
        ]
        result = agg.aggregate_by_hour(entries)
        assert result[0].hour == "2026-05-24T14"
        assert result[1].hour == "2026-05-24T16"

    def test_empty_entries(self):
        agg = _make_aggregator()
        assert agg.aggregate_by_hour([]) == []


class TestAggregateByDay:
    def test_same_day_grouped(self):
        agg = _make_aggregator()
        entries = [
            _entry(timestamp=datetime(2026, 5, 24, 10, 0)),
            _entry(timestamp=datetime(2026, 5, 24, 22, 0)),
        ]
        result = agg.aggregate_by_day(entries)
        assert len(result) == 1
        assert result[0].date == "2026-05-24"
        assert result[0].input_tokens == 2000

    def test_different_days_separated(self):
        agg = _make_aggregator()
        entries = [
            _entry(timestamp=datetime(2026, 5, 24, 10, 0)),
            _entry(timestamp=datetime(2026, 5, 25, 10, 0)),
        ]
        result = agg.aggregate_by_day(entries)
        assert len(result) == 2

    def test_sorted_chronologically(self):
        agg = _make_aggregator()
        entries = [
            _entry(timestamp=datetime(2026, 5, 26, 10, 0)),
            _entry(timestamp=datetime(2026, 5, 24, 10, 0)),
        ]
        result = agg.aggregate_by_day(entries)
        assert result[0].date == "2026-05-24"
        assert result[1].date == "2026-05-26"

    def test_models_used_collected(self):
        agg = _make_aggregator()
        entries = [
            _entry(model="claude-sonnet-4-6"),
            _entry(model="claude-opus-4-6"),
        ]
        result = agg.aggregate_by_day(entries)
        assert set(result[0].models_used) == {"claude-sonnet-4-6", "claude-opus-4-6"}


class TestAggregateByMonth:
    def test_same_month_grouped(self):
        agg = _make_aggregator()
        entries = [
            _entry(timestamp=datetime(2026, 5, 1, 10, 0)),
            _entry(timestamp=datetime(2026, 5, 31, 10, 0)),
        ]
        result = agg.aggregate_by_month(entries)
        assert len(result) == 1
        assert result[0].month == "2026-05"

    def test_different_months_separated(self):
        agg = _make_aggregator()
        entries = [
            _entry(timestamp=datetime(2026, 4, 15, 10, 0)),
            _entry(timestamp=datetime(2026, 5, 15, 10, 0)),
        ]
        result = agg.aggregate_by_month(entries)
        assert len(result) == 2
        assert result[0].month == "2026-04"
        assert result[1].month == "2026-05"

    def test_includes_daily_data(self):
        agg = _make_aggregator()
        entries = [
            _entry(timestamp=datetime(2026, 5, 24, 10, 0)),
            _entry(timestamp=datetime(2026, 5, 25, 10, 0)),
        ]
        result = agg.aggregate_by_month(entries)
        assert len(result[0].daily_data) == 2


class TestFilterByDateRange:
    def test_filters_correctly(self):
        agg = _make_aggregator()
        entries = [
            _entry(timestamp=datetime(2026, 5, 23, 10, 0)),
            _entry(timestamp=datetime(2026, 5, 24, 10, 0)),
            _entry(timestamp=datetime(2026, 5, 25, 10, 0)),
        ]
        filtered = agg.filter_by_date_range(
            entries,
            start_date=datetime(2026, 5, 24, 0, 0),
            end_date=datetime(2026, 5, 24, 23, 59, 59),
        )
        assert len(filtered) == 1
        assert filtered[0].timestamp.day == 24

    def test_empty_range(self):
        agg = _make_aggregator()
        entries = [_entry(timestamp=datetime(2026, 5, 24, 10, 0))]
        filtered = agg.filter_by_date_range(
            entries,
            start_date=datetime(2026, 6, 1),
            end_date=datetime(2026, 6, 30),
        )
        assert filtered == []


class TestGetDateRangePresets:
    def test_returns_expected_keys(self):
        agg = _make_aggregator()
        presets = agg.get_date_range_presets()
        expected_keys = {"today", "yesterday", "last_3_days", "this_week", "this_month"}
        assert set(presets.keys()) == expected_keys

    def test_each_preset_is_tuple(self):
        agg = _make_aggregator()
        presets = agg.get_date_range_presets()
        for key, value in presets.items():
            assert isinstance(value, tuple) and len(value) == 2
