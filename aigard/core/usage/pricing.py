"""
定价管理器 - 管理模型定价配置
"""
import re
from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class ModelPricing:
    """模型定价"""
    input_price: float  # 每百万 token 的价格
    output_price: float
    cache_creation_price: float
    cache_read_price: float


def normalize_model_name(model: str) -> str:
    """
    归一化模型名称，统一处理各种变体格式。

    规则（按优先级）：
    1. 去掉 anthropic/ 前缀
    2. 去掉末尾的日期后缀（-YYYYMMDD）
    3. 统一 claude-3-X-Y → claude-3.X 格式
    4. 转为小写

    示例：
    - claude-sonnet-4-6-20251101       → claude-sonnet-4-6
    - claude-3-5-sonnet-20241022       → claude-3-5-sonnet
    - anthropic/claude-opus-4-0        → claude-opus-4
    - claude-haiku-4-5-20251001        → claude-haiku-4-5
    - Claude-Sonnet-4-6                → claude-sonnet-4-6
    """
    if not model:
        return model

    name = model.lower().strip()

    # 去掉前缀
    if name.startswith('anthropic/'):
        name = name[len('anthropic/'):]

    # 去掉末尾 -YYYYMMDD 日期后缀
    name = re.sub(r'-\d{8}$', '', name)

    # 去掉末尾 -YYYYMMDDHHMMSS 日期时间后缀（更长的情况）
    name = re.sub(r'-\d{14}$', '', name)

    # 去掉末尾 -preview、-beta、-latest 等修饰词（保留版本号）
    name = re.sub(r'-(preview|beta|latest|exp|experimental)$', '', name)

    return name


class PricingManager:
    """管理模型定价"""

    # 默认定价表（美元/百万 tokens）
    # key 统一使用归一化后的模型名
    DEFAULT_PRICING: Dict[str, ModelPricing] = {

        # ===== Claude 4 系列 =====
        'claude-opus-4': ModelPricing(
            input_price=15.0,
            output_price=75.0,
            cache_creation_price=18.75,
            cache_read_price=1.50,
        ),
        'claude-sonnet-4': ModelPricing(
            input_price=3.0,
            output_price=15.0,
            cache_creation_price=3.75,
            cache_read_price=0.30,
        ),
        'claude-sonnet-4-5': ModelPricing(
            input_price=3.0,
            output_price=15.0,
            cache_creation_price=3.75,
            cache_read_price=0.30,
        ),
        'claude-sonnet-4-6': ModelPricing(
            input_price=3.0,
            output_price=15.0,
            cache_creation_price=3.75,
            cache_read_price=0.30,
        ),
        'claude-haiku-4-5': ModelPricing(
            input_price=0.80,
            output_price=4.0,
            cache_creation_price=1.0,
            cache_read_price=0.08,
        ),

        # ===== Claude 3.7 系列 =====
        'claude-sonnet-3-7': ModelPricing(
            input_price=3.0,
            output_price=15.0,
            cache_creation_price=3.75,
            cache_read_price=0.30,
        ),

        # ===== Claude 3.5 系列 =====
        'claude-opus-3-5': ModelPricing(
            input_price=15.0,
            output_price=75.0,
            cache_creation_price=18.75,
            cache_read_price=1.50,
        ),
        'claude-sonnet-3-5': ModelPricing(
            input_price=3.0,
            output_price=15.0,
            cache_creation_price=3.75,
            cache_read_price=0.30,
        ),
        'claude-3-5-sonnet': ModelPricing(
            input_price=3.0,
            output_price=15.0,
            cache_creation_price=3.75,
            cache_read_price=0.30,
        ),
        'claude-haiku-3-5': ModelPricing(
            input_price=0.80,
            output_price=4.0,
            cache_creation_price=1.0,
            cache_read_price=0.08,
        ),
        'claude-3-5-haiku': ModelPricing(
            input_price=0.80,
            output_price=4.0,
            cache_creation_price=1.0,
            cache_read_price=0.08,
        ),

        # ===== Claude 3 系列 =====
        'claude-opus-3': ModelPricing(
            input_price=15.0,
            output_price=75.0,
            cache_creation_price=18.75,
            cache_read_price=1.50,
        ),
        'claude-3-opus': ModelPricing(
            input_price=15.0,
            output_price=75.0,
            cache_creation_price=18.75,
            cache_read_price=1.50,
        ),
        'claude-sonnet-3': ModelPricing(
            input_price=3.0,
            output_price=15.0,
            cache_creation_price=3.75,
            cache_read_price=0.30,
        ),
        'claude-3-sonnet': ModelPricing(
            input_price=3.0,
            output_price=15.0,
            cache_creation_price=3.75,
            cache_read_price=0.30,
        ),
        'claude-haiku-3': ModelPricing(
            input_price=0.25,
            output_price=1.25,
            cache_creation_price=0.30,
            cache_read_price=0.03,
        ),
        'claude-3-haiku': ModelPricing(
            input_price=0.25,
            output_price=1.25,
            cache_creation_price=0.30,
            cache_read_price=0.03,
        ),

        # ===== Claude 2 系列 =====
        'claude-2': ModelPricing(
            input_price=8.0,
            output_price=24.0,
            cache_creation_price=0.0,
            cache_read_price=0.0,
        ),
        'claude-2-0': ModelPricing(
            input_price=8.0,
            output_price=24.0,
            cache_creation_price=0.0,
            cache_read_price=0.0,
        ),
        'claude-2-1': ModelPricing(
            input_price=8.0,
            output_price=24.0,
            cache_creation_price=0.0,
            cache_read_price=0.0,
        ),
        'claude-instant-1': ModelPricing(
            input_price=1.63,
            output_price=5.51,
            cache_creation_price=0.0,
            cache_read_price=0.0,
        ),
    }

    # 前缀匹配表：当精确匹配失败时，按前缀找最近的已知模型
    # 优先级：越具体的前缀越靠前
    _PREFIX_FALLBACK = [
        ('claude-opus-4',    'claude-opus-4'),
        ('claude-sonnet-4-6', 'claude-sonnet-4-6'),
        ('claude-sonnet-4-5', 'claude-sonnet-4-5'),
        ('claude-sonnet-4',  'claude-sonnet-4'),
        ('claude-haiku-4-5', 'claude-haiku-4-5'),
        ('claude-haiku-4',   'claude-haiku-4-5'),
        ('claude-sonnet-3-7', 'claude-sonnet-3-7'),
        ('claude-opus-3-5',  'claude-opus-3-5'),
        ('claude-sonnet-3-5', 'claude-sonnet-3-5'),
        ('claude-3-5-sonnet', 'claude-3-5-sonnet'),
        ('claude-haiku-3-5', 'claude-haiku-3-5'),
        ('claude-3-5-haiku', 'claude-3-5-haiku'),
        ('claude-opus-3',    'claude-opus-3'),
        ('claude-3-opus',    'claude-3-opus'),
        ('claude-sonnet-3',  'claude-sonnet-3'),
        ('claude-3-sonnet',  'claude-3-sonnet'),
        ('claude-haiku-3',   'claude-haiku-3'),
        ('claude-3-haiku',   'claude-3-haiku'),
        ('claude-2',         'claude-2'),
        ('claude-instant',   'claude-instant-1'),
        ('claude-',          'claude-sonnet-4-6'),  # 兜底：未知 Claude 用 Sonnet 4.6
    ]

    # 兜底定价：完全无法识别的模型
    _FALLBACK_PRICING = ModelPricing(
        input_price=3.0,
        output_price=15.0,
        cache_creation_price=3.75,
        cache_read_price=0.30,
    )

    def __init__(self, custom_pricing: Optional[Dict[str, ModelPricing]] = None):
        self.pricing = self.DEFAULT_PRICING.copy()
        if custom_pricing:
            self.pricing.update(custom_pricing)

    def has_pricing(self, model: str) -> bool:
        """检查模型是否有精确定价（归一化后精确匹配）"""
        normalized = normalize_model_name(model)
        return normalized in self.pricing

    def get_pricing(self, model: str) -> ModelPricing:
        """
        获取模型定价，按以下顺序匹配：
        1. 精确匹配（归一化后）
        2. 前缀匹配
        3. 兜底定价
        """
        normalized = normalize_model_name(model)

        # 精确匹配
        if normalized in self.pricing:
            return self.pricing[normalized]

        # 前缀匹配
        for prefix, target_key in self._PREFIX_FALLBACK:
            if normalized.startswith(prefix):
                if target_key in self.pricing:
                    return self.pricing[target_key]

        return self._FALLBACK_PRICING

    def calculate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cache_creation_tokens: int,
        cache_read_tokens: int,
    ) -> float:
        """计算费用（美元）"""
        p = self.get_pricing(model)
        return (
            (input_tokens / 1_000_000) * p.input_price +
            (output_tokens / 1_000_000) * p.output_price +
            (cache_creation_tokens / 1_000_000) * p.cache_creation_price +
            (cache_read_tokens / 1_000_000) * p.cache_read_price
        )

    def update_pricing(self, model: str, pricing: ModelPricing):
        self.pricing[normalize_model_name(model)] = pricing

    def get_all_pricing(self) -> Dict[str, ModelPricing]:
        return self.pricing.copy()

    def to_dict(self) -> Dict[str, dict]:
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
        custom_pricing = {}
        for model, pricing_data in data.items():
            custom_pricing[normalize_model_name(model)] = ModelPricing(
                input_price=pricing_data['input_price'],
                output_price=pricing_data['output_price'],
                cache_creation_price=pricing_data.get('cache_creation_price', 0.0),
                cache_read_price=pricing_data.get('cache_read_price', 0.0),
            )
        return cls(custom_pricing)
