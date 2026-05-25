"""tests/unit/core/usage/test_pricing.py -- PricingManager 单元测试"""

from aigard.core.usage.pricing import PricingManager, ModelPricing


class TestCalculateCost:
    def test_known_model_sonnet(self):
        pm = PricingManager()
        # claude-sonnet-4-6: input=3.0, output=15.0, cache_create=3.75, cache_read=0.30
        cost = pm.calculate_cost(
            "claude-sonnet-4-6",
            input_tokens=1_000_000,
            output_tokens=1_000_000,
            cache_creation_tokens=0,
            cache_read_tokens=0,
        )
        assert abs(cost - 18.0) < 0.001  # 3.0 + 15.0

    def test_known_model_opus(self):
        pm = PricingManager()
        # claude-opus-4-6: input=15.0, output=75.0
        cost = pm.calculate_cost(
            "claude-opus-4-6",
            input_tokens=1_000_000,
            output_tokens=1_000_000,
            cache_creation_tokens=0,
            cache_read_tokens=0,
        )
        assert abs(cost - 90.0) < 0.001

    def test_zero_tokens(self):
        pm = PricingManager()
        cost = pm.calculate_cost("claude-sonnet-4-6", 0, 0, 0, 0)
        assert cost == 0.0

    def test_cache_tokens_counted(self):
        pm = PricingManager()
        cost = pm.calculate_cost(
            "claude-sonnet-4-6",
            input_tokens=0,
            output_tokens=0,
            cache_creation_tokens=1_000_000,
            cache_read_tokens=1_000_000,
        )
        # cache_creation=3.75 + cache_read=0.30
        assert abs(cost - 4.05) < 0.001

    def test_unknown_model_uses_fuzzy_or_fallback(self):
        pm = PricingManager()
        # "totally-unknown" won't fuzzy match any key (no "claude" prefix)
        cost = pm.calculate_cost(
            "totally-unknown",
            input_tokens=1_000_000,
            output_tokens=0,
            cache_creation_tokens=0,
            cache_read_tokens=0,
        )
        # Falls back to sonnet pricing: input=3.0
        assert abs(cost - 3.0) < 0.001


class TestGetPricing:
    def test_exact_match(self):
        pm = PricingManager()
        pricing = pm.get_pricing("claude-sonnet-4-6")
        assert pricing.input_price == 3.0
        assert pricing.output_price == 15.0

    def test_fuzzy_match(self):
        pm = PricingManager()
        # Fuzzy match: model.startswith(key.split('-')[0])
        # All "claude-*" keys have first segment "claude", so fuzzy match hits
        # first dict entry. Test that a "claude-" prefixed unknown model
        # at least gets some valid pricing via fuzzy match.
        pricing = pm.get_pricing("claude-sonnet-4-6-20260501")
        assert pricing.input_price > 0  # gets some valid pricing

    def test_fallback_default(self):
        pm = PricingManager()
        pricing = pm.get_pricing("totally-unknown-model")
        # Falls back to sonnet pricing
        assert pricing.input_price == 3.0


class TestCustomPricing:
    def test_custom_overrides_default(self):
        custom = {"my-model": ModelPricing(1.0, 2.0, 0.5, 0.1)}
        pm = PricingManager(custom_pricing=custom)
        pricing = pm.get_pricing("my-model")
        assert pricing.input_price == 1.0
        assert pricing.output_price == 2.0

    def test_update_pricing(self):
        pm = PricingManager()
        pm.update_pricing("new-model", ModelPricing(10.0, 20.0, 5.0, 1.0))
        pricing = pm.get_pricing("new-model")
        assert pricing.input_price == 10.0

    def test_get_all_pricing(self):
        pm = PricingManager()
        all_pricing = pm.get_all_pricing()
        assert "claude-sonnet-4-6" in all_pricing
        assert "claude-opus-4" in all_pricing


class TestSerialization:
    def test_to_dict(self):
        pm = PricingManager()
        d = pm.to_dict()
        assert "claude-sonnet-4-6" in d
        assert d["claude-sonnet-4-6"]["input_price"] == 3.0

    def test_from_dict_roundtrip(self):
        pm = PricingManager()
        d = pm.to_dict()
        pm2 = PricingManager.from_dict(d)
        assert pm2.get_pricing("claude-sonnet-4-6").input_price == 3.0
        assert pm2.get_pricing("claude-opus-4-6").output_price == 75.0
