"""
# [CN] 数据聚合器 - 按时间维度聚合数据
"""
from typing import List, Dict
from datetime import datetime, timedelta
from collections import defaultdict
from .models import UsageEntry, DailySummary, HourlySummary, MonthlySummary, ModelBreakdown
from .calculator import UsageCalculator


class UsageAggregator:
    # [CN] """聚合使用数据"""

    def __init__(self, calculator: UsageCalculator):
        """
        初始化聚合器

        Args:
            calculator: 使用计算器
        """
        self.calculator = calculator

    def aggregate_by_hour(self, entries: List[UsageEntry]) -> List[HourlySummary]:
        """
        按小时聚合

        Args:
            entries: 使用记录列表

        Returns:
            小时汇总列表
        """
        hourly_data = defaultdict(list)

        # [CN] # 按小时分组
        for entry in entries:
            hour_key = entry.timestamp.strftime('%Y-%m-%dT%H')
            hourly_data[hour_key].append(entry)

        # [CN] # 生成汇总
        summaries = []
        for hour_key in sorted(hourly_data.keys()):
            hour_entries = hourly_data[hour_key]
            summary = self._create_hourly_summary(hour_key, hour_entries)
            summaries.append(summary)

        return summaries

    def aggregate_by_day(self, entries: List[UsageEntry]) -> List[DailySummary]:
        """
        按日聚合

        Args:
            entries: 使用记录列表

        Returns:
            日汇总列表
        """
        daily_data = defaultdict(list)

        # [CN] # 按日分组
        for entry in entries:
            date_key = entry.timestamp.strftime('%Y-%m-%d')
            daily_data[date_key].append(entry)

        # [CN] # 生成汇总
        summaries = []
        for date_key in sorted(daily_data.keys()):
            day_entries = daily_data[date_key]
            summary = self._create_daily_summary(date_key, day_entries)
            summaries.append(summary)

        return summaries

    def aggregate_by_month(self, entries: List[UsageEntry]) -> List[MonthlySummary]:
        """
        按月聚合

        Args:
            entries: 使用记录列表

        Returns:
            月汇总列表
        """
        monthly_data = defaultdict(list)

        # [CN] # 按月分组
        for entry in entries:
            month_key = entry.timestamp.strftime('%Y-%m')
            monthly_data[month_key].append(entry)

        # [CN] # 生成汇总
        summaries = []
        for month_key in sorted(monthly_data.keys()):
            month_entries = monthly_data[month_key]
            summary = self._create_monthly_summary(month_key, month_entries)
            summaries.append(summary)

        return summaries

    def _create_hourly_summary(self, hour: str, entries: List[UsageEntry]) -> HourlySummary:
        # [CN] """创建小时汇总"""
        token_breakdown = self.calculator.calculate_token_breakdown(entries)
        model_breakdowns = self.calculator.calculate_model_breakdown(entries)
        total_tokens = self.calculator.calculate_total_tokens(entries)
        total_cost = self.calculator.calculate_total_cost(entries)
        models_used = list(set(entry.model for entry in entries))
        request_count = sum(mb.request_count for mb in model_breakdowns)

        return HourlySummary(
            hour=hour,
            input_tokens=token_breakdown['input_tokens'],
            output_tokens=token_breakdown['output_tokens'],
            cache_creation_tokens=token_breakdown['cache_creation_tokens'],
            cache_read_tokens=token_breakdown['cache_read_tokens'],
            total_tokens=total_tokens,
            total_cost=total_cost,
            models_used=models_used,
            model_breakdowns=model_breakdowns,
            request_count=request_count
        )

    def _create_daily_summary(self, date: str, entries: List[UsageEntry]) -> DailySummary:
        # [CN] """创建日汇总"""
        token_breakdown = self.calculator.calculate_token_breakdown(entries)
        model_breakdowns = self.calculator.calculate_model_breakdown(entries)
        total_tokens = self.calculator.calculate_total_tokens(entries)
        total_cost = self.calculator.calculate_total_cost(entries)
        models_used = list(set(entry.model for entry in entries))
        request_count = sum(mb.request_count for mb in model_breakdowns)

        return DailySummary(
            date=date,
            input_tokens=token_breakdown['input_tokens'],
            output_tokens=token_breakdown['output_tokens'],
            cache_creation_tokens=token_breakdown['cache_creation_tokens'],
            cache_read_tokens=token_breakdown['cache_read_tokens'],
            total_tokens=total_tokens,
            total_cost=total_cost,
            models_used=models_used,
            model_breakdowns=model_breakdowns,
            request_count=request_count
        )

    def _create_monthly_summary(self, month: str, entries: List[UsageEntry]) -> MonthlySummary:
        # [CN] """创建月汇总"""
        token_breakdown = self.calculator.calculate_token_breakdown(entries)
        model_breakdowns = self.calculator.calculate_model_breakdown(entries)
        total_tokens = self.calculator.calculate_total_tokens(entries)
        total_cost = self.calculator.calculate_total_cost(entries)
        models_used = list(set(entry.model for entry in entries))
        request_count = sum(mb.request_count for mb in model_breakdowns)

        # [CN] 生成该月的每日数据
        daily_summaries = self.aggregate_by_day(entries)

        return MonthlySummary(
            month=month,
            input_tokens=token_breakdown['input_tokens'],
            output_tokens=token_breakdown['output_tokens'],
            cache_creation_tokens=token_breakdown['cache_creation_tokens'],
            cache_read_tokens=token_breakdown['cache_read_tokens'],
            total_tokens=total_tokens,
            total_cost=total_cost,
            models_used=models_used,
            model_breakdowns=model_breakdowns,
            daily_data=daily_summaries,
            request_count=request_count
        )

    def filter_by_date_range(
        self,
        entries: List[UsageEntry],
        start_date: datetime,
        end_date: datetime
    ) -> List[UsageEntry]:
        """
        # [CN] 按日期范围筛选

        Args:
            # [CN] entries: 使用记录列表
            start_date: StartDate
            end_date: EndDate

        Returns:
            # [CN] 筛选后的记录列表
        """
        return [
            entry for entry in entries
            if start_date <= entry.timestamp <= end_date
        ]

    def get_date_range_presets(self) -> Dict[str, tuple]:
        """
        # [CN] 获取预设的日期范围

        Returns:
            DateRangeDictionary {Name: (StartDate, EndDate)}
        """
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = now

        return {
            'today': (today_start, today_end),
            'yesterday': (
                today_start - timedelta(days=1),
                today_start - timedelta(seconds=1)
            ),
            'last_3_days': (today_start - timedelta(days=2), today_end),
            'this_week': (
                today_start - timedelta(days=now.weekday()),
                today_end
            ),
            'this_month': (
                now.replace(day=1, hour=0, minute=0, second=0, microsecond=0),
                today_end
            ),
        }
