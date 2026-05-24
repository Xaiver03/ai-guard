"""
Claude 使用统计 API 路由
"""
from fastapi import APIRouter, HTTPException, Query
from datetime import datetime, timedelta
from typing import Optional, List
import logging
import os

from aigard.core.usage import (
    ClaudeDataLoader,
    UsageCalculator,
    UsageAggregator,
    PricingManager,
    UsageCache,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/usage", tags=["usage"])


def _get_usage_config() -> dict:
    """从 config.toml 读取 [usage] 配置"""
    try:
        import main as _main_mod
        return _main_mod.CFG.get("usage", {})
    except Exception:
        return {}


# 从 config.toml 读取配置
_usage_cfg = _get_usage_config()
_claude_dir = os.path.expanduser(_usage_cfg.get("claude_data_dir", "~/.claude"))
_cache_ttl = _usage_cfg.get("cache_ttl", 300)

# 全局实例（使用 config.toml 配置）
pricing_manager = PricingManager()
calculator = UsageCalculator(pricing_manager)
aggregator = UsageAggregator(calculator)
loader = ClaudeDataLoader(claude_dir=_claude_dir)
cache = UsageCache()


def _ensure_cache():
    """确保缓存中有数据，如果没有则从 JSONL 加载"""
    if cache.has_data():
        return

    logger.info("首次加载 Claude 使用数据到缓存...")
    _rebuild_cache()


def _rebuild_cache():
    """重建缓存"""
    entries = loader.load_all_usage()
    if not entries:
        return

    # 按日聚合并保存
    daily_summaries = aggregator.aggregate_by_day(entries)
    daily_data = []
    for s in daily_summaries:
        daily_data.append({
            'date': s.date,
            'input_tokens': s.input_tokens,
            'output_tokens': s.output_tokens,
            'cache_creation_tokens': s.cache_creation_tokens,
            'cache_read_tokens': s.cache_read_tokens,
            'total_tokens': s.total_tokens,
            'total_cost': s.total_cost,
            'models_used': s.models_used,
            'model_breakdowns': [
                {
                    'model_name': mb.model_name,
                    'input_tokens': mb.input_tokens,
                    'output_tokens': mb.output_tokens,
                    'cache_creation_tokens': mb.cache_creation_tokens,
                    'cache_read_tokens': mb.cache_read_tokens,
                    'total_tokens': mb.total_tokens,
                    'cost': mb.cost,
                    'request_count': mb.request_count,
                }
                for mb in s.model_breakdowns
            ]
        })
    cache.save_daily(daily_data)

    # 按小时聚合并保存
    hourly_summaries = aggregator.aggregate_by_hour(entries)
    hourly_data = []
    for s in hourly_summaries:
        hourly_data.append({
            'hour': s.hour,
            'input_tokens': s.input_tokens,
            'output_tokens': s.output_tokens,
            'cache_creation_tokens': s.cache_creation_tokens,
            'cache_read_tokens': s.cache_read_tokens,
            'total_tokens': s.total_tokens,
            'total_cost': s.total_cost,
            'models_used': s.models_used,
        })
    cache.save_hourly(hourly_data)

    cache.set_last_update_time(datetime.now().isoformat())
    logger.info(f"缓存已更新: {len(daily_data)} 天, {len(hourly_data)} 小时")


@router.get("/summary")
async def get_summary(
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)"),
    preset: Optional[str] = Query(None, description="预设范围: today, yesterday, last_3_days, this_week, this_month")
):
    """获取使用统计总览"""
    try:
        _ensure_cache()
        start, end = _resolve_date_range(start_date, end_date, preset)
        return cache.get_summary(start, end)
    except Exception as e:
        logger.error(f"获取统计总览失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/daily")
async def get_daily_usage(
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)"),
    preset: Optional[str] = Query(None, description="预设范围")
):
    """获取每日使用统计"""
    try:
        _ensure_cache()
        start, end = _resolve_date_range(start_date, end_date, preset)
        return cache.get_daily(start, end)
    except Exception as e:
        logger.error(f"获取每日统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/hourly")
async def get_hourly_usage(
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)"),
    preset: Optional[str] = Query(None, description="预设范围")
):
    """获取每小时使用统计"""
    try:
        _ensure_cache()
        start, end = _resolve_date_range(start_date, end_date, preset)
        # 小时格式: YYYY-MM-DDTHH
        start_hour = f"{start}T00" if start else None
        end_hour = f"{end}T23" if end else None
        return cache.get_hourly(start_hour, end_hour)
    except Exception as e:
        logger.error(f"获取每小时统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/monthly")
async def get_monthly_usage():
    """获取每月使用统计"""
    try:
        _ensure_cache()
        daily = cache.get_daily()

        # 从日数据聚合成月数据
        monthly = {}
        for d in daily:
            month = d['date'][:7]
            if month not in monthly:
                monthly[month] = {
                    'month': month,
                    'input_tokens': 0,
                    'output_tokens': 0,
                    'cache_creation_tokens': 0,
                    'cache_read_tokens': 0,
                    'total_tokens': 0,
                    'total_cost': 0,
                    'models_used': set(),
                }
            m = monthly[month]
            m['input_tokens'] += d['input_tokens']
            m['output_tokens'] += d['output_tokens']
            m['cache_creation_tokens'] += d['cache_creation_tokens']
            m['cache_read_tokens'] += d['cache_read_tokens']
            m['total_tokens'] += d['total_tokens']
            m['total_cost'] += d['total_cost']
            m['models_used'].update(d.get('models_used', []))

        result = []
        for m in sorted(monthly.values(), key=lambda x: x['month']):
            m['models_used'] = list(m['models_used'])
            m['total_cost'] = round(m['total_cost'], 4)
            result.append(m)

        return result
    except Exception as e:
        logger.error(f"获取每月统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models")
async def get_model_stats(
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)"),
    preset: Optional[str] = Query(None, description="预设范围")
):
    """获取模型使用统计"""
    try:
        _ensure_cache()
        start, end = _resolve_date_range(start_date, end_date, preset)
        daily = cache.get_daily(start, end)

        # 从日数据聚合模型统计
        model_stats = {}
        for d in daily:
            for mb in d.get('model_breakdowns', []):
                name = mb['model_name']
                if name not in model_stats:
                    model_stats[name] = {
                        'model_name': name,
                        'input_tokens': 0,
                        'output_tokens': 0,
                        'cache_creation_tokens': 0,
                        'cache_read_tokens': 0,
                        'total_tokens': 0,
                        'cost': 0,
                        'request_count': 0,
                    }
                s = model_stats[name]
                s['input_tokens'] += mb.get('input_tokens', 0)
                s['output_tokens'] += mb.get('output_tokens', 0)
                s['cache_creation_tokens'] += mb.get('cache_creation_tokens', 0)
                s['cache_read_tokens'] += mb.get('cache_read_tokens', 0)
                s['total_tokens'] += mb.get('total_tokens', 0)
                s['cost'] += mb.get('cost', 0)
                s['request_count'] += mb.get('request_count', 0)

        result = sorted(model_stats.values(), key=lambda x: x['cost'], reverse=True)
        for r in result:
            r['cost'] = round(r['cost'], 4)

        return result
    except Exception as e:
        logger.error(f"获取模型统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects")
async def get_projects():
    """获取所有项目列表"""
    try:
        projects = loader.get_projects()
        return {"projects": projects}
    except Exception as e:
        logger.error(f"获取项目列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pricing")
async def get_pricing():
    """获取定价配置"""
    return pricing_manager.to_dict()


@router.post("/pricing")
async def update_pricing(pricing_data: dict):
    """更新定价配置"""
    try:
        global pricing_manager, calculator, aggregator
        pricing_manager = PricingManager.from_dict(pricing_data)
        calculator = UsageCalculator(pricing_manager)
        aggregator = UsageAggregator(calculator)
        return {"status": "success", "message": "定价配置已更新"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/refresh")
async def refresh_data():
    """刷新数据（重新解析 JSONL 并更新缓存）"""
    try:
        cache.clear()
        _rebuild_cache()
        return {
            "status": "success",
            "message": "数据已刷新",
            "last_update": cache.get_last_update_time()
        }
    except Exception as e:
        logger.error(f"刷新数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _resolve_date_range(
    start_date: Optional[str],
    end_date: Optional[str],
    preset: Optional[str]
) -> tuple:
    """解析日期范围"""
    now = datetime.now()
    today = now.strftime('%Y-%m-%d')

    if preset:
        if preset == 'today':
            return today, today
        elif preset == 'yesterday':
            yesterday = (now - timedelta(days=1)).strftime('%Y-%m-%d')
            return yesterday, yesterday
        elif preset == 'last_3_days':
            start = (now - timedelta(days=2)).strftime('%Y-%m-%d')
            return start, today
        elif preset == 'this_week':
            start = (now - timedelta(days=now.weekday())).strftime('%Y-%m-%d')
            return start, today
        elif preset == 'this_month':
            start = now.replace(day=1).strftime('%Y-%m-%d')
            return start, today

    return start_date, end_date
