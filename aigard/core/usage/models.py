"""
数据模型定义
"""
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime


@dataclass(slots=True)
class UsageEntry:
    """单条使用记录"""
    timestamp: datetime
    model: str
    input_tokens: int
    output_tokens: int
    cache_creation_tokens: int
    cache_read_tokens: int
    cost: float
    project: str
    session_id: str
    source: str = "claude-code"  # DataSource:claude-code, codex, cursor


@dataclass(slots=True)
class ModelBreakdown:
    """模型使用明细"""
    model_name: str
    input_tokens: int
    output_tokens: int
    cache_creation_tokens: int
    cache_read_tokens: int
    total_tokens: int
    cost: float
    request_count: int


@dataclass(slots=True)
class HourlySummary:
    """小时汇总"""
    hour: str  # Format: "2026-05-24T14"
    input_tokens: int
    output_tokens: int
    cache_creation_tokens: int
    cache_read_tokens: int
    total_tokens: int
    total_cost: float
    models_used: List[str]
    model_breakdowns: List[ModelBreakdown]
    request_count: int = 0  # 总请求次数


@dataclass(slots=True)
class DailySummary:
    """日汇总"""
    date: str  # Format: "2026-05-24"
    input_tokens: int
    output_tokens: int
    cache_creation_tokens: int
    cache_read_tokens: int
    total_tokens: int
    total_cost: float
    models_used: List[str]
    model_breakdowns: List[ModelBreakdown]
    request_count: int = 0  # [CN] 总请求次数


@dataclass(slots=True)
class MonthlySummary:
    """月汇总"""
    month: str  # Format: "2026-05"
    input_tokens: int
    output_tokens: int
    cache_creation_tokens: int
    cache_read_tokens: int
    total_tokens: int
    total_cost: float
    models_used: List[str]
    model_breakdowns: List[ModelBreakdown]
    daily_data: List[DailySummary]
    request_count: int = 0  # 总请求次数


@dataclass(slots=True)
class SessionSummary:
    """会话汇总"""
    session_id: str
    project: str
    start_time: datetime
    end_time: datetime
    duration_seconds: int
    message_count: int
    total_tokens: int
    input_tokens: int
    output_tokens: int
    cache_creation_tokens: int
    cache_read_tokens: int
    total_cost: float
    models_used: List[str]

