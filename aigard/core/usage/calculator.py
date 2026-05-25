"""
使用计算器 - 计算 Token 和费用
"""
from typing import List, Dict, Set
from .models import UsageEntry, ModelBreakdown
from .pricing import PricingManager, normalize_model_name


class UsageCalculator:
    """计算使用统计"""

    def __init__(self, pricing_manager: PricingManager):
        self.pricing_manager = pricing_manager

    def calculate_total_tokens(self, entries: List[UsageEntry]) -> int:
        return sum(
            entry.input_tokens +
            entry.output_tokens +
            entry.cache_creation_tokens +
            entry.cache_read_tokens
            for entry in entries
        )

    def calculate_total_cost(self, entries: List[UsageEntry]) -> float:
        total = 0.0
        for entry in entries:
            if entry.cost > 0:
                total += entry.cost
            else:
                total += self.pricing_manager.calculate_cost(
                    entry.model,
                    entry.input_tokens,
                    entry.output_tokens,
                    entry.cache_creation_tokens,
                    entry.cache_read_tokens,
                )
        return total

    def calculate_coverage(self, entries: List[UsageEntry]) -> dict:
        """
        计算 Token 覆盖率（有定价的 token 占比）

        Returns:
            {
                'coverage_percent': float,    # 0-100
                'total_tokens': int,
                'priced_tokens': int,
                'unknown_models': list[str],  # 归一化后的模型名
            }
        """
        total_tokens = 0
        priced_tokens = 0
        unknown_models: Set[str] = set()

        for entry in entries:
            tokens = (
                entry.input_tokens +
                entry.output_tokens +
                entry.cache_creation_tokens +
                entry.cache_read_tokens
            )
            total_tokens += tokens

            if self.pricing_manager.has_pricing(entry.model):
                priced_tokens += tokens
            else:
                unknown_models.add(normalize_model_name(entry.model))

        coverage = (priced_tokens / total_tokens * 100) if total_tokens > 0 else 100.0

        return {
            'coverage_percent': round(coverage, 1),
            'total_tokens': total_tokens,
            'priced_tokens': priced_tokens,
            'unknown_models': sorted(unknown_models),
        }

    def calculate_model_breakdown(self, entries: List[UsageEntry]) -> List[ModelBreakdown]:
        model_stats: Dict[str, dict] = {}

        for entry in entries:
            # 用归一化名作 key，保留原始名展示
            model = entry.model
            norm = normalize_model_name(model)
            key = norm  # 相同归一化名的不同原始名合并

            if key not in model_stats:
                model_stats[key] = {
                    'display_name': model,  # 第一个遇到的原始名
                    'input_tokens': 0,
                    'output_tokens': 0,
                    'cache_creation_tokens': 0,
                    'cache_read_tokens': 0,
                    'cost': 0.0,
                    'request_count': 0,
                }

            s = model_stats[key]
            s['input_tokens'] += entry.input_tokens
            s['output_tokens'] += entry.output_tokens
            s['cache_creation_tokens'] += entry.cache_creation_tokens
            s['cache_read_tokens'] += entry.cache_read_tokens
            s['request_count'] += 1

            if entry.cost > 0:
                s['cost'] += entry.cost
            else:
                s['cost'] += self.pricing_manager.calculate_cost(
                    entry.model,
                    entry.input_tokens,
                    entry.output_tokens,
                    entry.cache_creation_tokens,
                    entry.cache_read_tokens,
                )

        breakdowns = []
        for norm_name, s in model_stats.items():
            total_tokens = (
                s['input_tokens'] +
                s['output_tokens'] +
                s['cache_creation_tokens'] +
                s['cache_read_tokens']
            )
            breakdowns.append(ModelBreakdown(
                model_name=norm_name,
                input_tokens=s['input_tokens'],
                output_tokens=s['output_tokens'],
                cache_creation_tokens=s['cache_creation_tokens'],
                cache_read_tokens=s['cache_read_tokens'],
                total_tokens=total_tokens,
                cost=s['cost'],
                request_count=s['request_count'],
            ))

        breakdowns.sort(key=lambda x: x.cost, reverse=True)
        return breakdowns

    def calculate_token_breakdown(self, entries: List[UsageEntry]) -> dict:
        breakdown = {
            'input_tokens': 0,
            'output_tokens': 0,
            'cache_creation_tokens': 0,
            'cache_read_tokens': 0,
        }
        for entry in entries:
            breakdown['input_tokens'] += entry.input_tokens
            breakdown['output_tokens'] += entry.output_tokens
            breakdown['cache_creation_tokens'] += entry.cache_creation_tokens
            breakdown['cache_read_tokens'] += entry.cache_read_tokens
        return breakdown

