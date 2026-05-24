"""tests/integration/test_usage_pipeline.py -- 使用统计全链路集成测试
Loader -> Calculator -> Aggregator -> Cache
"""

import json
from datetime import datetime
from aigard.core.usage.loader import ClaudeDataLoader
from aigard.core.usage.calculator import UsageCalculator
from aigard.core.usage.aggregator import UsageAggregator
from aigard.core.usage.pricing import PricingManager
from aigard.core.usage.cache import UsageCache


def _write_jsonl(path, entries):
    """Write JSONL entries to a file."""
    lines = []
    for e in entries:
        lines.append(json.dumps(e))
    path.write_text("\n".join(lines) + "\n")


def _assistant_record(timestamp, model="claude-sonnet-4-6",
                      input_tokens=1000, output_tokens=500):
    return {
        "type": "assistant",
        "timestamp": timestamp,
        "message": {
            "model": model,
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cache_creation_input_tokens": 200,
                "cache_read_input_tokens": 100,
            }
        }
    }


class TestFullPipeline:
    def test_loader_to_calculator_to_aggregator_to_cache(self, tmp_path):
        # 1. Create JSONL data
        proj_dir = tmp_path / "claude" / "projects" / "test-proj"
        proj_dir.mkdir(parents=True)
        _write_jsonl(proj_dir / "session1.jsonl", [
            _assistant_record("2026-05-24T10:00:00Z"),
            _assistant_record("2026-05-24T14:00:00Z"),
            _assistant_record("2026-05-25T10:00:00Z"),
        ])

        # 2. Load
        loader = ClaudeDataLoader(str(tmp_path / "claude"))
        entries = loader.load_all_usage()
        assert len(entries) == 3

        # 3. Calculate
        pm = PricingManager()
        calc = UsageCalculator(pm)
        total_tokens = calc.calculate_total_tokens(entries)
        assert total_tokens == 3 * 1800  # 1000+500+200+100 each

        total_cost = calc.calculate_total_cost(entries)
        assert total_cost > 0

        # 4. Aggregate
        agg = UsageAggregator(calc)
        daily = agg.aggregate_by_day(entries)
        assert len(daily) == 2  # 2 different days

        hourly = agg.aggregate_by_hour(entries)
        assert len(hourly) == 3  # 3 different hours

        # 5. Cache to SQLite
        cache = UsageCache(str(tmp_path / "cache"))
        daily_data = []
        for s in daily:
            daily_data.append({
                "date": s.date,
                "input_tokens": s.input_tokens,
                "output_tokens": s.output_tokens,
                "cache_creation_tokens": s.cache_creation_tokens,
                "cache_read_tokens": s.cache_read_tokens,
                "total_tokens": s.total_tokens,
                "total_cost": s.total_cost,
                "models_used": s.models_used,
                "model_breakdowns": [],
            })
        cache.save_daily(daily_data)

        hourly_data = []
        for s in hourly:
            hourly_data.append({
                "hour": s.hour,
                "input_tokens": s.input_tokens,
                "output_tokens": s.output_tokens,
                "cache_creation_tokens": s.cache_creation_tokens,
                "cache_read_tokens": s.cache_read_tokens,
                "total_tokens": s.total_tokens,
                "total_cost": s.total_cost,
                "models_used": s.models_used,
            })
        cache.save_hourly(hourly_data)

        # 6. Verify from cache
        assert cache.has_data() is True
        cached_daily = cache.get_daily()
        assert len(cached_daily) == 2
        assert cached_daily[0]["date"] == "2026-05-24"
        assert cached_daily[0]["input_tokens"] == 2000  # 2 entries on 24th

        summary = cache.get_summary()
        assert summary["total_tokens"] == total_tokens
        assert summary["active_days"] == 2

    def test_pipeline_empty_data(self, tmp_path):
        loader = ClaudeDataLoader(str(tmp_path / "empty"))
        entries = loader.load_all_usage()
        assert entries == []

        pm = PricingManager()
        calc = UsageCalculator(pm)
        assert calc.calculate_total_tokens(entries) == 0
        assert calc.calculate_total_cost(entries) == 0.0

    def test_pipeline_multi_model(self, tmp_path):
        proj_dir = tmp_path / "claude" / "projects" / "proj"
        proj_dir.mkdir(parents=True)
        _write_jsonl(proj_dir / "s1.jsonl", [
            _assistant_record("2026-05-24T10:00:00Z", model="claude-sonnet-4-6"),
            _assistant_record("2026-05-24T11:00:00Z", model="claude-opus-4-6", input_tokens=5000),
        ])

        loader = ClaudeDataLoader(str(tmp_path / "claude"))
        entries = loader.load_all_usage()

        pm = PricingManager()
        calc = UsageCalculator(pm)
        breakdowns = calc.calculate_model_breakdown(entries)
        assert len(breakdowns) == 2
        # opus should have higher cost (15.0/M vs 3.0/M)
        assert breakdowns[0].model_name == "claude-opus-4-6"
