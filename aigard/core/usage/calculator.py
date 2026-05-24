"""
使用计算器 - 计算 Token 和费用
"""
from typing import List
from .models import UsageEntry, ModelBreakdown
from .pricing import PricingManager


class UsageCalculator:
    """计算使用统计"""

    def __init__(self, pricing_manager: PricingManager):
        """
        初始化计算器

        Args:
            pricing_manager: 定价管理器
        """
        self.pricing_manager = pricing_manager

    def calculate_total_tokens(self, entries: List[UsageEntry]) -> int:
        """
        计算总 token 数

        Args:
            entries: 使用记录列表

        Returns:
            总 token 数
        """
        return sum(
            entry.input_tokens +
            entry.output_tokens +
            entry.cache_creation_tokens +
            entry.cache_read_tokens
            for entry in entries
        )

    def calculate_total_cost(self, entries: List[UsageEntry]) -> float:
        """
        计算总费用

        Args:
            entries: 使用记录列表

        Returns:
            总费用（美元）
        """
        total = 0.0
        for entry in entries:
            # 如果记录中已有费用，使用记录的费用
            if entry.cost > 0:
                total += entry.cost
            else:
                # 否则根据定价计算
                cost = self.pricing_manager.calculate_cost(
                    entry.model,
                    entry.input_tokens,
                    entry.output_tokens,
                    entry.cache_creation_tokens,
                    entry.cache_read_tokens
                )
                total += cost

        return total

    def calculate_model_breakdown(self, entries: List[UsageEntry]) -> List[ModelBreakdown]:
        """
        按模型统计使用情况

        Args:
            entries: 使用记录列表

        Returns:
            模型使用明细列表
        """
        model_stats = {}

        for entry in entries:
            model = entry.model
            if model not in model_stats:
                model_stats[model] = {
                    'input_tokens': 0,
                    'output_tokens': 0,
                    'cache_creation_tokens': 0,
                    'cache_read_tokens': 0,
                    'cost': 0.0,
                    'request_count': 0,
                }

            stats = model_stats[model]
            stats['input_tokens'] += entry.input_tokens
            stats['output_tokens'] += entry.output_tokens
            stats['cache_creation_tokens'] += entry.cache_creation_tokens
            stats['cache_read_tokens'] += entry.cache_read_tokens
            stats['request_count'] += 1

            # 计算费用
            if entry.cost > 0:
                stats['cost'] += entry.cost
            else:
                cost = self.pricing_manager.calculate_cost(
                    entry.model,
                    entry.input_tokens,
                    entry.output_tokens,
                    entry.cache_creation_tokens,
                    entry.cache_read_tokens
                )
                stats['cost'] += cost

        # 转换为 ModelBreakdown 列表
        breakdowns = []
        for model, stats in model_stats.items():
            total_tokens = (
                stats['input_tokens'] +
                stats['output_tokens'] +
                stats['cache_creation_tokens'] +
                stats['cache_read_tokens']
            )

            breakdowns.append(ModelBreakdown(
                model_name=model,
                input_tokens=stats['input_tokens'],
                output_tokens=stats['output_tokens'],
                cache_creation_tokens=stats['cache_creation_tokens'],
                cache_read_tokens=stats['cache_read_tokens'],
                total_tokens=total_tokens,
                cost=stats['cost'],
                request_count=stats['request_count']
            ))

        # 按费用降序排序
        breakdowns.sort(key=lambda x: x.cost, reverse=True)

        return breakdowns

    def calculate_token_breakdown(self, entries: List[UsageEntry]) -> dict:
        """
        计算 token 类型分布

        Args:
            entries: 使用记录列表

        Returns:
            Token 分布字典
        """
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
