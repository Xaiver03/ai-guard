"""
定价管理器 - 管理模型定价配置
"""
import re
from typing import Dict, Optional
from dataclasses import dataclass


@dataclass(slots=True)
class ModelPricing:
    """模型定价"""
    input_price: float  # 每百万 token 的价格
    output_price: float
    cache_creation_price: float
    cache_read_price: float


def normalize_model_name(model: str) -> str:
    """
    归一化模型名称,统一处理各种变体格式.

    规则(按优先级):
    1. 去掉 anthropic/ 等前缀
    2. 去掉末尾的日期后缀(-YYYYMMDD)
    3. 统一点号和横线格式:claude-4.6-opus → claude-opus-4-6
    4. 去掉 -thinking 等后缀
    5. 转为小写

    示例:
    - claude-sonnet-4-6-20251101       → claude-sonnet-4-6
    - claude-4.6-opus                  → claude-opus-4-6
    - claude-opus-4-6-thinking         → claude-opus-4-6
    - anthropic/claude-opus-4-0        → claude-opus-4
    - kimi-for-coding                  → kimi-for-coding
    """
    if not model:
        return model

    name = model.lower().strip()

    # 去掉前缀
    if name.startswith('anthropic/'):
        name = name[len('anthropic/'):]

    # 去掉末尾 -YYYYMMDD 日期后缀
    name = re.sub(r'-\d{8}$', '', name)

    # 去掉末尾 -YYYYMMDDHHMMSS 日期时间后缀(更长的情况)
    name = re.sub(r'-\d{14}$', '', name)

    # 去掉末尾 -preview,-beta,-latest,-thinking 等修饰词
    name = re.sub(r'-(preview|beta|latest|exp|experimental|thinking)$', '', name)

    # 统一 claude-4.6-opus → claude-opus-4-6 格式
    match = re.match(r'^claude-(\d+)\.(\d+)-(opus|sonnet|haiku)$', name)
    if match:
        major, minor, tier = match.groups()
        name = f'claude-{tier}-{major}-{minor}'

    # 统一 claude-opus-4.6 → claude-opus-4-6 格式(点号改横线)
    match = re.match(r'^claude-(opus|sonnet|haiku)-(\d+)\.(\d+)$', name)
    if match:
        tier, major, minor = match.groups()
        name = f'claude-{tier}-{major}-{minor}'

    return name


class PricingManager:
    """管理模型定价"""

    # 默认定价表(美元/百万 tokens)
    # key 统一使用归一化后的模型名
    DEFAULT_PRICING: Dict[str, ModelPricing] = {

        # ===== Claude 4 系列 =====
        'claude-opus-4': ModelPricing(
            input_price=15.0,
            output_price=75.0,
            cache_creation_price=18.75,
            cache_read_price=1.50,
        ),
        'claude-opus-4-5': ModelPricing(
            input_price=15.0,
            output_price=75.0,
            cache_creation_price=18.75,
            cache_read_price=1.50,
        ),
        'claude-opus-4-6': ModelPricing(
            input_price=15.0,
            output_price=75.0,
            cache_creation_price=18.75,
            cache_read_price=1.50,
        ),
        'claude-opus-4-7': ModelPricing(
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

        # ===== DeepSeek 系列 =====
        'deepseek-v4-pro': ModelPricing(
            input_price=0.44,
            output_price=0.88,
            cache_creation_price=0.44,
            cache_read_price=0.044,
        ),
        'deepseek-v4-flash': ModelPricing(
            input_price=0.10,
            output_price=0.20,
            cache_creation_price=0.10,
            cache_read_price=0.01,
        ),
        'deepseek-v3': ModelPricing(
            input_price=0.27,
            output_price=1.10,
            cache_creation_price=0.27,
            cache_read_price=0.07,
        ),
        'deepseek-r1': ModelPricing(
            input_price=0.55,
            output_price=2.19,
            cache_creation_price=0.55,
            cache_read_price=0.14,
        ),

        # ===== Kimi / Moonshot 系列 =====
        'kimi-for-coding': ModelPricing(
            input_price=0.55,
            output_price=2.20,
            cache_creation_price=0.55,
            cache_read_price=0.14,
        ),
        'kimi-k2': ModelPricing(
            input_price=0.55,
            output_price=2.20,
            cache_creation_price=0.55,
            cache_read_price=0.14,
        ),

        # ===== MiniMax 系列 =====
        'minimax-m2.7': ModelPricing(
            input_price=0.28,
            output_price=1.20,
            cache_creation_price=0.28,
            cache_read_price=0.07,
        ),
        'minimax-m2.7-highspeed': ModelPricing(
            input_price=0.28,
            output_price=1.20,
            cache_creation_price=0.28,
            cache_read_price=0.07,
        ),
        'minimax-m2': ModelPricing(
            input_price=0.26,
            output_price=1.00,
            cache_creation_price=0.26,
            cache_read_price=0.06,
        ),

        # ===== GLM / 智谱 系列 =====
        'glm-5.1': ModelPricing(
            input_price=0.98,
            output_price=3.08,
            cache_creation_price=0.98,
            cache_read_price=0.25,
        ),
        'glm-4.5': ModelPricing(
            input_price=0.60,
            output_price=2.20,
            cache_creation_price=0.60,
            cache_read_price=0.15,
        ),

        # ===== MiMo / 小米 系列 =====
        'mimo-v2.5-pro': ModelPricing(
            input_price=1.00,
            output_price=3.00,
            cache_creation_price=1.00,
            cache_read_price=0.25,
        ),

        # ===== GPT 系列 =====
        'gpt-5-codex': ModelPricing(
            input_price=1.25,
            output_price=10.0,
            cache_creation_price=1.25,
            cache_read_price=0.125,
        ),
        'gpt-5.1-codex': ModelPricing(
            input_price=1.25,
            output_price=10.0,
            cache_creation_price=1.25,
            cache_read_price=0.125,
        ),
        'gpt-5.2-codex': ModelPricing(
            input_price=1.25,
            output_price=10.0,
            cache_creation_price=1.25,
            cache_read_price=0.125,
        ),
        'gpt-5.3-codex': ModelPricing(
            input_price=1.25,
            output_price=10.0,
            cache_creation_price=1.25,
            cache_read_price=0.125,
        ),
        'gpt-4o': ModelPricing(
            input_price=2.50,
            output_price=10.0,
            cache_creation_price=2.50,
            cache_read_price=1.25,
        ),
        'gpt-4o-mini': ModelPricing(
            input_price=0.15,
            output_price=0.60,
            cache_creation_price=0.15,
            cache_read_price=0.075,
        ),
        'gpt-4-turbo': ModelPricing(
            input_price=10.0,
            output_price=30.0,
            cache_creation_price=0.0,
            cache_read_price=0.0,
        ),
        'o3': ModelPricing(
            input_price=2.0,
            output_price=8.0,
            cache_creation_price=2.0,
            cache_read_price=0.50,
        ),
        'o3-mini': ModelPricing(
            input_price=1.10,
            output_price=4.40,
            cache_creation_price=1.10,
            cache_read_price=0.275,
        ),
        'o4-mini': ModelPricing(
            input_price=1.10,
            output_price=4.40,
            cache_creation_price=1.10,
            cache_read_price=0.275,
        ),
        'codex-mini': ModelPricing(
            input_price=1.50,
            output_price=6.0,
            cache_creation_price=1.50,
            cache_read_price=0.375,
        ),

        # ===== Gemini 系列 =====
        'gemini-2.5-pro': ModelPricing(
            input_price=1.25,
            output_price=10.0,
            cache_creation_price=0.3125,
            cache_read_price=0.3125,
        ),
        'gemini-2.5-flash': ModelPricing(
            input_price=0.15,
            output_price=0.60,
            cache_creation_price=0.0375,
            cache_read_price=0.0375,
        ),

        # ===== Qwen / 通义 系列 =====
        'qwen3-coder': ModelPricing(
            input_price=0.50,
            output_price=2.0,
            cache_creation_price=0.50,
            cache_read_price=0.125,
        ),
        'qwen3-235b': ModelPricing(
            input_price=0.80,
            output_price=2.0,
            cache_creation_price=0.80,
            cache_read_price=0.20,
        ),

        # ===== 零价/特殊模型 =====
        '<synthetic>': ModelPricing(
            input_price=0.0,
            output_price=0.0,
            cache_creation_price=0.0,
            cache_read_price=0.0,
        ),
        'unknown': ModelPricing(
            input_price=3.0,
            output_price=15.0,
            cache_creation_price=3.75,
            cache_read_price=0.30,
        ),
    }

    # 前缀匹配表:当精确匹配失败时,按前缀找最近的已知模型
    # 优先级:越具体的前缀越靠前
    _PREFIX_FALLBACK = [
        # Claude 4 系列
        ('claude-opus-4-7',   'claude-opus-4-7'),
        ('claude-opus-4-6',   'claude-opus-4-6'),
        ('claude-opus-4-5',   'claude-opus-4-5'),
        ('claude-opus-4',     'claude-opus-4'),
        ('claude-sonnet-4-6', 'claude-sonnet-4-6'),
        ('claude-sonnet-4-5', 'claude-sonnet-4-5'),
        ('claude-sonnet-4',   'claude-sonnet-4'),
        ('claude-haiku-4-5',  'claude-haiku-4-5'),
        ('claude-haiku-4',    'claude-haiku-4-5'),
        # Claude 3.7
        ('claude-sonnet-3-7', 'claude-sonnet-3-7'),
        # Claude 3.5
        ('claude-opus-3-5',   'claude-opus-3-5'),
        ('claude-sonnet-3-5', 'claude-sonnet-3-5'),
        ('claude-3-5-sonnet', 'claude-3-5-sonnet'),
        ('claude-haiku-3-5',  'claude-haiku-3-5'),
        ('claude-3-5-haiku',  'claude-3-5-haiku'),
        # Claude 3
        ('claude-opus-3',     'claude-opus-3'),
        ('claude-3-opus',     'claude-3-opus'),
        ('claude-sonnet-3',   'claude-sonnet-3'),
        ('claude-3-sonnet',   'claude-3-sonnet'),
        ('claude-haiku-3',    'claude-haiku-3'),
        ('claude-3-haiku',    'claude-3-haiku'),
        # Claude 2
        ('claude-2',          'claude-2'),
        ('claude-instant',    'claude-instant-1'),
        # DeepSeek
        ('deepseek-v4-pro',   'deepseek-v4-pro'),
        ('deepseek-v4-flash', 'deepseek-v4-flash'),
        ('deepseek-v3',       'deepseek-v3'),
        ('deepseek-r1',       'deepseek-r1'),
        ('deepseek',          'deepseek-v4-pro'),
        # Kimi
        ('kimi-for-coding',   'kimi-for-coding'),
        ('kimi-k2',           'kimi-k2'),
        ('kimi',              'kimi-k2'),
        ('moonshot',          'kimi-k2'),
        # MiniMax
        ('minimax-m2.7',      'minimax-m2.7'),
        ('minimax-m2',        'minimax-m2'),
        ('minimax',           'minimax-m2.7'),
        # GLM
        ('glm-5.1',           'glm-5.1'),
        ('glm-4.5',           'glm-4.5'),
        ('glm',               'glm-5.1'),
        # MiMo
        ('mimo-v2.5-pro',     'mimo-v2.5-pro'),
        ('mimo',              'mimo-v2.5-pro'),
        # GPT
        ('gpt-5.3-codex',     'gpt-5.3-codex'),
        ('gpt-5.2-codex',     'gpt-5.2-codex'),
        ('gpt-5.1-codex',     'gpt-5.1-codex'),
        ('gpt-5-codex',       'gpt-5-codex'),
        ('gpt-4o-mini',       'gpt-4o-mini'),
        ('gpt-4o',            'gpt-4o'),
        ('gpt-4-turbo',       'gpt-4-turbo'),
        ('o4-mini',           'o4-mini'),
        ('o3-mini',           'o3-mini'),
        ('o3',                'o3'),
        ('codex-mini',        'codex-mini'),
        ('gpt',               'gpt-4o'),
        # Gemini
        ('gemini-2.5-pro',    'gemini-2.5-pro'),
        ('gemini-2.5-flash',  'gemini-2.5-flash'),
        ('gemini',            'gemini-2.5-flash'),
        # Qwen
        ('qwen3-coder',       'qwen3-coder'),
        ('qwen3-235b',        'qwen3-235b'),
        ('qwen',              'qwen3-coder'),
        # 兜底
        ('claude-',           'claude-sonnet-4-6'),
    ]

    # 兜底定价:完全无法识别的模型
    _FALLBACK_PRICING = ModelPricing(
        input_price=3.0,
        output_price=15.0,
        cache_creation_price=3.75,
        cache_read_price=0.30,
    )

    def __init__(self, custom_pricing: Optional[Dict[str, ModelPricing]] = None,
                 repository=None):
        self.pricing = self.DEFAULT_PRICING.copy()

        # 从数据库加载覆盖
        if repository is not None:
            self.repository = repository
            db_overrides = repository.get_all_overrides()
            self.pricing.update(db_overrides)
        else:
            self.repository = None

        # 应用内存中的自定义定价(用于测试)
        if custom_pricing:
            self.pricing.update(custom_pricing)

    def has_pricing(self, model: str) -> bool:
        """检查模型是否有精确定价(归一化后精确匹配)"""
        normalized = normalize_model_name(model)
        return normalized in self.pricing

    def get_pricing(self, model: str) -> ModelPricing:
        """
        获取模型定价,按以下顺序匹配:
        1. 精确匹配(归一化后)
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
        """计算费用(美元)"""
        p = self.get_pricing(model)
        return (
            (input_tokens / 1_000_000) * p.input_price +
            (output_tokens / 1_000_000) * p.output_price +
            (cache_creation_tokens / 1_000_000) * p.cache_creation_price +
            (cache_read_tokens / 1_000_000) * p.cache_read_price
        )

    def update_pricing(self, model: str, pricing: ModelPricing, persist: bool = True):
        """更新模型定价"""
        normalized = normalize_model_name(model)
        self.pricing[normalized] = pricing

        # 持久化到数据库
        if persist and self.repository is not None:
            self.repository.save_override(model, pricing)

    def delete_pricing(self, model: str, persist: bool = True) -> bool:
        """删除模型定价覆盖(恢复默认),返回是否删除成功"""
        normalized = normalize_model_name(model)

        只能删除非默认定价
        if normalized in self.DEFAULT_PRICING:
            return False

        if normalized in self.pricing:
            del self.pricing[normalized]

        从数据库删除
        if persist and self.repository is not None:
            return self.repository.delete_override(model)

        return True

    def reset_all_overrides(self):
        """重置所有覆盖,恢复默认定价"""
        self.pricing = self.DEFAULT_PRICING.copy()

        if self.repository is not None:
            self.repository.clear_all_overrides()

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
