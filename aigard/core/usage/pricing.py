"""
定价管理器 - 管理模型定价配置
"""
from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class ModelPricing:
    """模型定价"""
    input_price: float  # 每百万 token 的价格
    output_price: float
    cache_creation_price: float
    cache_read_price: float


class PricingManager:
    """管理模型定价"""

    # 默认定价表（美元/百万 tokens）
    DEFAULT_PRICING = {
        # Claude 4.6
        'claude-opus-4-6': ModelPricing(
            input_price=15.0,
            output_price=75.0,
            cache_creation_price=18.75,
            cache_read_price=1.50
        ),
        'claude-sonnet-4-6': ModelPricing(
            input_price=3.0,
            output_price=15.0,
            cache_creation_price=3.75,
            cache_read_price=0.30
        ),

        # Claude 4.5
        'claude-haiku-4-5': ModelPricing(
            input_price=0.80,
            output_price=4.0,
            cache_creation_price=1.0,
            cache_read_price=0.08
        ),

        # Claude 3.5
        'claude-3-5-sonnet-20241022': ModelPricing(
            input_price=3.0,
            output_price=15.0,
            cache_creation_price=3.75,
            cache_read_price=0.30
        ),
        'claude-3-5-haiku-20241022': ModelPricing(
            input_price=0.80,
            output_price=4.0,
            cache_creation_price=1.0,
            cache_read_price=0.08
        ),

        # Claude 3 Opus
        'claude-3-opus-20240229': ModelPricing(
            input_price=15.0,
            output_price=75.0,
            cache_creation_price=18.75,
            cache_read_price=1.50
        ),
    }

    def __init__(self, custom_pricing: Optional[Dict[str, ModelPricing]] = None):
        """
        初始化定价管理器

        Args:
            custom_pricing: 自定义定价表
        """
        self.pricing = self.DEFAULT_PRICING.copy()
        if custom_pricing:
            self.pricing.update(custom_pricing)

    def get_pricing(self, model: str) -> ModelPricing:
        """
        获取模型定价

        Args:
            model: 模型名称

        Returns:
            ModelPricing 对象
        """
        # 精确匹配
        if model in self.pricing:
            return self.pricing[model]

        # 模糊匹配（处理版本号变化）
        for key, pricing in self.pricing.items():
            if model.startswith(key.split('-')[0]):
                return pricing

        # 默认使用 Sonnet 定价
        return self.pricing.get('claude-sonnet-4-6', ModelPricing(3.0, 15.0, 3.75, 0.30))

    def calculate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cache_creation_tokens: int,
        cache_read_tokens: int
    ) -> float:
        """
        计算费用

        Args:
            model: 模型名称
            input_tokens: 输入 token 数
            output_tokens: 输出 token 数
            cache_creation_tokens: 缓存创建 token 数
            cache_read_tokens: 缓存读取 token 数

        Returns:
            费用（美元）
        """
        pricing = self.get_pricing(model)

        cost = (
            (input_tokens / 1_000_000) * pricing.input_price +
            (output_tokens / 1_000_000) * pricing.output_price +
            (cache_creation_tokens / 1_000_000) * pricing.cache_creation_price +
            (cache_read_tokens / 1_000_000) * pricing.cache_read_price
        )

        return cost

    def update_pricing(self, model: str, pricing: ModelPricing):
        """
        更新模型定价

        Args:
            model: 模型名称
            pricing: 新的定价
        """
        self.pricing[model] = pricing

    def get_all_pricing(self) -> Dict[str, ModelPricing]:
        """
        获取所有定价

        Returns:
            定价字典
        """
        return self.pricing.copy()

    def to_dict(self) -> Dict[str, dict]:
        """
        转换为字典格式（用于 API 返回）

        Returns:
            定价字典
        """
        result = {}
        for model, pricing in self.pricing.items():
            result[model] = {
                'input_price': pricing.input_price,
                'output_price': pricing.output_price,
                'cache_creation_price': pricing.cache_creation_price,
                'cache_read_price': pricing.cache_read_price,
            }
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, dict]) -> 'PricingManager':
        """
        从字典创建定价管理器

        Args:
            data: 定价字典

        Returns:
            PricingManager 对象
        """
        custom_pricing = {}
        for model, pricing_data in data.items():
            custom_pricing[model] = ModelPricing(
                input_price=pricing_data['input_price'],
                output_price=pricing_data['output_price'],
                cache_creation_price=pricing_data['cache_creation_price'],
                cache_read_price=pricing_data['cache_read_price'],
            )
        return cls(custom_pricing)
