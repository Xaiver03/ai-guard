"""
# [CN] 核心功能模块
# [CN] - monitor: 系统指标采集
# [CN] - advisor: 进程安全评估
# [CN] - killer: 进程干预操作
# [CN] - alerter: 分级告警通知
# [CN] - whitelist: 白名单管理
"""

from .monitor import collect_metrics, collect_ai_processes, collect_all_processes, MetricsHistory, Metrics, ProcessInfo
from .advisor import advise, advise_list, ProcessAdvice, CPU_CAUTION_PCT, IDLE_MIN_MINUTES
from .killer import pause_process, resume_process, kill_process, ActionResult
from .alerter import Alerter
from .whitelist import WhitelistManager

__all__ = [
    # monitor
    'collect_metrics',
    'collect_ai_processes',
    'collect_all_processes',
    'MetricsHistory',
    'Metrics',
    'ProcessInfo',
    # advisor
    'advise',
    'advise_list',
    'ProcessAdvice',
    'CPU_CAUTION_PCT',
    'IDLE_MIN_MINUTES',
    # killer
    'pause_process',
    'resume_process',
    'kill_process',
    'ActionResult',
    # alerter
    'Alerter',
    # whitelist
    'WhitelistManager',
]
