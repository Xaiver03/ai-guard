"""
Claude 使用统计 API 路由
"""
from fastapi import APIRouter, HTTPException, Query
from datetime import datetime, timedelta
from typing import Optional, List
import logging
import os
import threading

from aigard.core.usage import (
    ClaudeDataLoader,
    UsageCalculator,
    UsageAggregator,
    PricingManager,
    PricingRepository,
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
pricing_repository = PricingRepository()
pricing_manager = PricingManager(repository=pricing_repository)
calculator = UsageCalculator(pricing_manager)
aggregator = UsageAggregator(calculator)
loader = ClaudeDataLoader(claude_dir=_claude_dir)
cache = UsageCache()

# 缓存重建锁（防止并发刷新导致数据不一致）
_rebuild_lock = threading.Lock()


def _ensure_cache():
    """确保缓存中有数据，如果没有则从 JSONL 加载"""
    if cache.has_data():
        return

    logger.info("首次加载 Claude 使用数据到缓存...")
    _rebuild_cache()


def _rebuild_cache(project: Optional[str] = None):
    """重建缓存（支持按项目筛选），线程安全"""
    with _rebuild_lock:
        if project:
            entries = loader.load_project_usage(project)
        else:
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
        cache.save_hourly(hourly_data)

        # 计算并保存 coverage
        coverage = calculator.calculate_coverage(entries)
        cache.save_coverage(coverage)

        cache.set_last_update_time(datetime.now().isoformat())
        logger.info(f"缓存已更新: {len(daily_data)} 天, {len(hourly_data)} 小时, 覆盖率: {coverage['coverage_percent']}%")


@router.get("/summary")
async def get_summary(
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)"),
    preset: Optional[str] = Query(None, description="预设范围: today, yesterday, last_3_days, this_week, this_month"),
    project: Optional[str] = Query(None, description="项目名称（筛选特定项目）")
):
    """获取使用统计总览"""
    try:
        # 项目筛选：实时计算（不使用缓存）
        if project:
            entries = loader.load_project_usage(project)
            if not entries:
                return {
                    'total_cost': 0, 'total_tokens': 0, 'input_tokens': 0, 'output_tokens': 0,
                    'cache_creation_tokens': 0, 'cache_read_tokens': 0, 'models_used': [],
                    'model_breakdowns': [], 'coverage': {'coverage_percent': 100.0, 'total_tokens': 0, 'priced_tokens': 0, 'unknown_models': []}
                }

            # 时间范围过滤
            start, end = _resolve_date_range(start_date, end_date, preset)
            if start:
                entries = [e for e in entries if e.timestamp.strftime('%Y-%m-%d') >= start]
            if end:
                entries = [e for e in entries if e.timestamp.strftime('%Y-%m-%d') <= end]

            # 计算汇总
            total_cost = sum(e.cost for e in entries)
            total_tokens = sum(e.input_tokens + e.output_tokens + e.cache_creation_tokens + e.cache_read_tokens for e in entries)
            input_tokens = sum(e.input_tokens for e in entries)
            output_tokens = sum(e.output_tokens for e in entries)
            cache_creation_tokens = sum(e.cache_creation_tokens for e in entries)
            cache_read_tokens = sum(e.cache_read_tokens for e in entries)

            # 模型统计
            model_breakdown = calculator.calculate_model_breakdown(entries)
            models_used = list(set(e.model for e in entries))

            # 覆盖率
            coverage = calculator.calculate_coverage(entries)

            return {
                'total_cost': round(total_cost, 4),
                'total_tokens': total_tokens,
                'input_tokens': input_tokens,
                'output_tokens': output_tokens,
                'cache_creation_tokens': cache_creation_tokens,
                'cache_read_tokens': cache_read_tokens,
                'models_used': models_used,
                'model_breakdowns': [
                    {
                        'model_name': mb.model_name,
                        'input_tokens': mb.input_tokens,
                        'output_tokens': mb.output_tokens,
                        'cache_creation_tokens': mb.cache_creation_tokens,
                        'cache_read_tokens': mb.cache_read_tokens,
                        'total_tokens': mb.total_tokens,
                        'cost': round(mb.cost, 4),
                        'request_count': mb.request_count,
                    }
                    for mb in model_breakdown
                ],
                'coverage': coverage,
            }

        # 全量数据：使用缓存
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
    preset: Optional[str] = Query(None, description="预设范围"),
    project: Optional[str] = Query(None, description="项目名称（筛选特定项目）")
):
    """获取每日使用统计"""
    try:
        # 项目筛选：实时计算
        if project:
            entries = loader.load_project_usage(project)
            if not entries:
                return []

            # 时间范围过滤
            start, end = _resolve_date_range(start_date, end_date, preset)
            if start:
                entries = [e for e in entries if e.timestamp.strftime('%Y-%m-%d') >= start]
            if end:
                entries = [e for e in entries if e.timestamp.strftime('%Y-%m-%d') <= end]

            # 按日聚合
            daily_summaries = aggregator.aggregate_by_day(entries)
            return [
                {
                    'date': s.date,
                    'input_tokens': s.input_tokens,
                    'output_tokens': s.output_tokens,
                    'cache_creation_tokens': s.cache_creation_tokens,
                    'cache_read_tokens': s.cache_read_tokens,
                    'total_tokens': s.total_tokens,
                    'total_cost': round(s.total_cost, 4),
                    'models_used': s.models_used,
                    'model_breakdowns': [
                        {
                            'model_name': mb.model_name,
                            'input_tokens': mb.input_tokens,
                            'output_tokens': mb.output_tokens,
                            'cache_creation_tokens': mb.cache_creation_tokens,
                            'cache_read_tokens': mb.cache_read_tokens,
                            'total_tokens': mb.total_tokens,
                            'cost': round(mb.cost, 4),
                            'request_count': mb.request_count,
                        }
                        for mb in s.model_breakdowns
                    ],
                }
                for s in daily_summaries
            ]

        # 全量数据：使用缓存
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
    preset: Optional[str] = Query(None, description="预设范围"),
    project: Optional[str] = Query(None, description="项目名称（筛选特定项目）")
):
    """获取每小时使用统计"""
    try:
        # 项目筛选：实时计算
        if project:
            entries = loader.load_project_usage(project)
            if not entries:
                return []

            # 时间范围过滤
            if preset == '24h':
                now = datetime.now()
                start_dt = now - timedelta(hours=24)
                entries = [e for e in entries if e.timestamp >= start_dt]
            else:
                start, end = _resolve_date_range(start_date, end_date, preset)
                if start:
                    entries = [e for e in entries if e.timestamp.strftime('%Y-%m-%d') >= start]
                if end:
                    entries = [e for e in entries if e.timestamp.strftime('%Y-%m-%d') <= end]

            # 按小时聚合
            hourly_summaries = aggregator.aggregate_by_hour(entries)
            return [
                {
                    'hour': s.hour,
                    'input_tokens': s.input_tokens,
                    'output_tokens': s.output_tokens,
                    'cache_creation_tokens': s.cache_creation_tokens,
                    'cache_read_tokens': s.cache_read_tokens,
                    'total_tokens': s.total_tokens,
                    'total_cost': round(s.total_cost, 4),
                    'models_used': s.models_used,
                    'model_breakdowns': [
                        {
                            'model_name': mb.model_name,
                            'input_tokens': mb.input_tokens,
                            'output_tokens': mb.output_tokens,
                            'cache_creation_tokens': mb.cache_creation_tokens,
                            'cache_read_tokens': mb.cache_read_tokens,
                            'total_tokens': mb.total_tokens,
                            'cost': round(mb.cost, 4),
                            'request_count': mb.request_count,
                        }
                        for mb in s.model_breakdowns
                    ],
                }
                for s in hourly_summaries
            ]

        # 全量数据：使用缓存
        _ensure_cache()

        # 24H 滚动窗口：精确到小时粒度
        if preset == '24h':
            now = datetime.now()
            start_dt = now - timedelta(hours=24)
            start_hour = start_dt.strftime('%Y-%m-%dT%H')
            end_hour = now.strftime('%Y-%m-%dT%H')
            return cache.get_hourly(start_hour, end_hour)

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


@router.get("/sessions")
async def get_sessions(
    project: Optional[str] = Query(None, description="项目名称（筛选特定项目）"),
    limit: Optional[int] = Query(50, description="返回数量限制"),
    offset: Optional[int] = Query(0, description="偏移量")
):
    """获取会话列表"""
    try:
        summaries = loader.load_session_summaries(project=project)

        # 分页
        total = len(summaries)
        paginated = summaries[offset:offset + limit]

        return {
            "total": total,
            "sessions": [
                {
                    "session_id": s.session_id,
                    "project": s.project,
                    "start_time": s.start_time.isoformat(),
                    "end_time": s.end_time.isoformat(),
                    "duration_seconds": s.duration_seconds,
                    "message_count": s.message_count,
                    "total_tokens": s.total_tokens,
                    "input_tokens": s.input_tokens,
                    "output_tokens": s.output_tokens,
                    "cache_creation_tokens": s.cache_creation_tokens,
                    "cache_read_tokens": s.cache_read_tokens,
                    "total_cost": round(s.total_cost, 4),
                    "models_used": s.models_used,
                }
                for s in paginated
            ]
        }
    except Exception as e:
        logger.error(f"获取会话列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pricing")
async def get_pricing():
    """获取定价配置"""
    return pricing_manager.to_dict()


@router.post("/pricing")
async def update_pricing(pricing_data: dict):
    """更新定价配置（单个模型或批量），自动持久化并重建缓存"""
    try:
        from aigard.core.usage.pricing import ModelPricing

        # 检测是单个模型格式还是批量格式
        if 'model' in pricing_data:
            # 单个模型格式: {"model": "xxx", "input": 1.0, ...}
            model = pricing_data['model']
            pricing = ModelPricing(
                input_price=pricing_data.get('input', 0.0),
                output_price=pricing_data.get('output', 0.0),
                cache_creation_price=pricing_data.get('cache_write', 0.0),
                cache_read_price=pricing_data.get('cache_read', 0.0),
            )
            pricing_manager.update_pricing(model, pricing, persist=True)
        else:
            # 批量格式: {"model1": {"input_price": 1.0, ...}, ...}
            for model, pricing_dict in pricing_data.items():
                pricing = ModelPricing(
                    input_price=pricing_dict['input_price'],
                    output_price=pricing_dict['output_price'],
                    cache_creation_price=pricing_dict.get('cache_creation_price', 0.0),
                    cache_read_price=pricing_dict.get('cache_read_price', 0.0),
                )
                pricing_manager.update_pricing(model, pricing, persist=True)

        # 后台异步重建缓存
        threading.Thread(target=_rebuild_cache, daemon=True).start()

        return {"status": "success", "message": "定价配置已更新，缓存正在重建"}
    except Exception as e:
        logger.error(f"更新定价失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/pricing/{model:path}")
async def delete_pricing(model: str):
    """删除单个模型的定价覆盖（恢复默认）"""
    try:
        success = pricing_manager.delete_pricing(model, persist=True)

        if not success:
            raise HTTPException(
                status_code=400,
                detail="无法删除内置默认定价"
            )

        # 后台异步重建缓存
        threading.Thread(target=_rebuild_cache, daemon=True).start()

        return {"status": "success", "message": f"已删除 {model} 的定价覆盖"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除定价失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pricing/reset")
async def reset_all_pricing():
    """重置所有定价覆盖，恢复默认"""
    try:
        pricing_manager.reset_all_overrides()

        # 后台异步重建缓存
        threading.Thread(target=_rebuild_cache, daemon=True).start()

        return {"status": "success", "message": "所有定价覆盖已重置"}
    except Exception as e:
        logger.error(f"重置定价失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/refresh")
async def refresh_data():
    """刷新数据（重新解析 JSONL 并更新缓存），线程安全"""
    try:
        with _rebuild_lock:
            cache.clear()
            # 直接在锁内重建，确保 clear + rebuild 是原子操作
            entries = loader.load_all_usage()
            if entries:
                daily_summaries = aggregator.aggregate_by_day(entries)
                daily_data = [{
                    'date': s.date,
                    'input_tokens': s.input_tokens,
                    'output_tokens': s.output_tokens,
                    'cache_creation_tokens': s.cache_creation_tokens,
                    'cache_read_tokens': s.cache_read_tokens,
                    'total_tokens': s.total_tokens,
                    'total_cost': s.total_cost,
                    'models_used': s.models_used,
                    'model_breakdowns': [{
                        'model_name': mb.model_name,
                        'input_tokens': mb.input_tokens,
                        'output_tokens': mb.output_tokens,
                        'cache_creation_tokens': mb.cache_creation_tokens,
                        'cache_read_tokens': mb.cache_read_tokens,
                        'total_tokens': mb.total_tokens,
                        'cost': mb.cost,
                        'request_count': mb.request_count,
                    } for mb in s.model_breakdowns]
                } for s in daily_summaries]
                cache.save_daily(daily_data)

                hourly_summaries = aggregator.aggregate_by_hour(entries)
                hourly_data = [{
                    'hour': s.hour,
                    'input_tokens': s.input_tokens,
                    'output_tokens': s.output_tokens,
                    'cache_creation_tokens': s.cache_creation_tokens,
                    'cache_read_tokens': s.cache_read_tokens,
                    'total_tokens': s.total_tokens,
                    'total_cost': s.total_cost,
                    'models_used': s.models_used,
                    'model_breakdowns': [{
                        'model_name': mb.model_name,
                        'input_tokens': mb.input_tokens,
                        'output_tokens': mb.output_tokens,
                        'cache_creation_tokens': mb.cache_creation_tokens,
                        'cache_read_tokens': mb.cache_read_tokens,
                        'total_tokens': mb.total_tokens,
                        'cost': mb.cost,
                        'request_count': mb.request_count,
                    } for mb in s.model_breakdowns]
                } for s in hourly_summaries]
                cache.save_hourly(hourly_data)

                coverage = calculator.calculate_coverage(entries)
                cache.save_coverage(coverage)
                cache.set_last_update_time(datetime.now().isoformat())
                logger.info(f"刷新完成: {len(daily_data)} 天, {len(hourly_data)} 小时")

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
            # 今天：本地零点到现在（起点固定）
            return today, today
        elif preset == '24h':
            # 24H 滚动窗口：可能跨昨天和今天
            yesterday = (now - timedelta(days=1)).strftime('%Y-%m-%d')
            return yesterday, today
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
