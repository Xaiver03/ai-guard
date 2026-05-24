"""tests/unit/core/usage/test_calculator.py -- UsageCalculator 单元测试"""

from datetime import datetime
from aigard.core.usage.calculator import UsageCalculator
from aigard.core.usage.pricing import PricingManager
from aigard.core.usage.models import UsageEntry


def _entry(**overrides):
    defaults = dict(
        timestamp=datetime(2026, 5, 24, 14, 0),
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


class TestCalculateTotalTokens:
    def test_single_entry(self):
        calc = UsageCalculator(PricingManager())
        entries = [_entry()]
        assert calc.calculate_total_tokens(entries) == 1800  # 1000+500+200+100

    def test_multiple_entries(self):
        calc = UsageCalculator(PricingManager())
        entries = [_entry(), _entry(input_tokens=2000)]
        total = calc.calculate_total_tokens(entries)
        assert total == 1800 + 2800  # second: 2000+500+200+100

    def test_empty_entries(self):
        calc = UsageCalculator(PricingManager())
        assert calc.calculate_total_tokens([]) == 0


class TestCalculateTotalCost:
    def test_calculates_from_pricing_when_cost_zero(self):
        calc = UsageCalculator(PricingManager())
        entries = [_entry(cost=0.0)]
        cost = calc.calculate_total_cost(entries)
        # sonnet: (1000/1M)*3 + (500/1M)*15 + (200/1M)*3.75 + (100/1M)*0.30
        expected = 0.003 + 0.0075 + 0.00075 + 0.00003
        assert abs(cost - expected) < 1e-6

    def test_uses_entry_cost_if_present(self):
        calc = UsageCalculator(PricingManager())
        entries = [_entry(cost=1.5)]
        cost = calc.calculate_total_cost(entries)
        assert cost == 1.5

    def test_empty_entries(self):
        calc = UsageCalculator(PricingManager())
        assert calc.calculate_total_cost([]) == 0.0


class TestCalculateModelBreakdown:
    def test_single_model(self):
        calc = UsageCalculator(PricingManager())
        entries = [_entry(), _entry()]
        breakdowns = calc.calculate_model_breakdown(entries)
        assert len(breakdowns) == 1
        assert breakdowns[0].model_name == "claude-sonnet-4-6"
        assert breakdowns[0].input_tokens == 2000
        assert breakdowns[0].request_count == 2

    def test_multiple_models_sorted_by_cost(self):
        calc = UsageCalculator(PricingManager())
        entries = [
            _entry(model="claude-sonnet-4-6"),
            _entry(model="claude-opus-4-6", input_tokens=10000, output_tokens=5000),
        ]
        breakdowns = calc.calculate_model_breakdown(entries)
        assert len(breakdowns) == 2
        # opus should be first (higher cost)
        assert breakdowns[0].model_name == "claude-opus-4-6"
        assert breakdowns[1].model_name == "claude-sonnet-4-6"

    def test_empty_entries(self):
        calc = UsageCalculator(PricingManager())
        assert calc.calculate_model_breakdown([]) == []


class TestCalculateTokenBreakdown:
    def test_sums_by_token_type(self):
        calc = UsageCalculator(PricingManager())
        entries = [
            _entry(input_tokens=1000, output_tokens=500, cache_creation_tokens=200, cache_read_tokens=100),
            _entry(input_tokens=2000, output_tokens=300, cache_creation_tokens=0, cache_read_tokens=50),
        ]
        bd = calc.calculate_token_breakdown(entries)
        assert bd["input_tokens"] == 3000
        assert bd["output_tokens"] == 800
        assert bd["cache_creation_tokens"] == 200
        assert bd["cache_read_tokens"] == 150

    def test_empty_entries(self):
        calc = UsageCalculator(PricingManager())
        bd = calc.calculate_token_breakdown([])
        assert all(v == 0 for v in bd.values())
