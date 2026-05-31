"""
后台线程模块 - 监控,自动终止,黑名单拦截,定时终止
"""

import time
import threading
from dataclasses import asdict

from aigard.core import (
    collect_metrics, collect_ai_processes, advise_list,
    kill_process, Alerter, MetricsHistory, WhitelistManager
)


class BackgroundThreads:
    """管理所有后台线程"""

    def __init__(self, config: dict, history: MetricsHistory, alerter: Alerter, whitelist: WhitelistManager):
        self.config = config
        self.history = history
        self.alerter = alerter
        self.whitelist = whitelist

        # SharedState
        self.latest_processes = []
        self.auto_kill_log = []
        self.lock = threading.Lock()

        # 运行时配置
        self.autokill_enabled = config.get("auto_kill", {}).get("enabled", False)
        self.blocked_processes = set()
        self.scheduled_kill_enabled = False
        self.scheduled_kill_interval = 10
        self.settings = {}
        self.settings_lock = threading.Lock()

        # JSONL 增量解析:记录每个文件的读取位置
        self._jsonl_offsets = {}  # {file_path: last_offset}

        # 条件变量:用于事件驱动的线程唤醒
        self._block_event = threading.Event()
        self._autokill_event = threading.Event()

        # 线程对象
        self._threads = []

    def start_all(self):
        """启动所有后台线程"""
        # 应用评分配置到 advisor 模块
        self._apply_scoring_config()

        self._threads = [
            threading.Thread(target=self._monitor_loop, daemon=True),
            threading.Thread(target=self._auto_kill_loop, daemon=True),
            threading.Thread(target=self._block_loop, daemon=True),
            threading.Thread(target=self._scheduled_kill_loop, daemon=True),
            threading.Thread(target=self._usage_refresh_loop, daemon=True),
        ]
        for t in self._threads:
            t.start()

    def _apply_scoring_config(self):
        """将配置应用到 advisor 模块"""
        import aigard.core.advisor as advisor_mod

        with self.settings_lock:
            scoring = self.settings.get("scoring", {})
            if "cpu_caution_pct" in scoring:
                advisor_mod.CPU_CAUTION_PCT = scoring["cpu_caution_pct"]
            if "idle_min_minutes" in scoring:
                advisor_mod.IDLE_MIN_MINUTES = scoring["idle_min_minutes"]

    def _monitor_loop(self):
        """监控线程:采集指标和进程列表"""
        from alert_history import record_alert

        while True:
            try:
                m = collect_metrics()
                level = self.alerter.check(m.to_dict())
                if level in ("warn", "crit"):
                    record_alert(level, f"内存 {m.mem_percent:.0f}% / Swap {m.swap_percent:.0f}%")
                m.alert_level = level
                self.history.push(m)

                watch_keywords = self.config.get("processes", {}).get("watch_keywords", ["claude", "node", "python"])
                procs = collect_ai_processes(watch_keywords)
                with self.lock:
                    self.latest_processes = advise_list([asdict(p) for p in procs])
            except Exception as e:
                print(f"[monitor error] {e}")

            with self.settings_lock:
                interval = self.settings.get("monitor", {}).get("interval_sec", 1)
            time.sleep(interval)

    def _auto_kill_loop(self):
        """自动终止线程:内存超阈值时终止 safe 进程"""
        last_killed_time = 0.0

        while True:
            if not self.autokill_enabled:
                # 禁用时休眠,等待被唤醒(toggle API 会 set 事件)
                self._autokill_event.wait(timeout=60)
                self._autokill_event.clear()
                continue

            with self.settings_lock:
                ak = self.settings.get("auto_kill", {})
            mem_trigger = ak.get("mem_trigger_pct", 85)
            swap_trigger = ak.get("swap_trigger_pct", 75)
            target_mem = ak.get("target_mem_pct", 70)
            cooldown = ak.get("cooldown_sec", 120)

            latest = self.history.latest
            if not latest:
                time.sleep(15)
                continue

            mem_pct = latest.get("mem_percent", 0)
            swap_pct = latest.get("swap_percent", 0)

            if mem_pct < mem_trigger and swap_pct < swap_trigger:
                time.sleep(15)
                continue
            if time.time() - last_killed_time < cooldown:
                time.sleep(15)
                continue

            with self.lock:
                # 过滤掉白名单中的进程
                candidates = [
                    p for p in self.latest_processes
                    if p.get("risk") == "safe" and not self.whitelist.is_whitelisted(p)
                ]
            candidates.sort(key=lambda p: p.get("mem_mb", 0), reverse=True)

            killed_count = 0
            freed_mb = 0.0
            for proc in candidates:
                cur = self.history.latest
                if cur and cur.get("mem_percent", 100) < target_mem:
                    break
                pid = proc["pid"]
                result = kill_process(pid)
                if result.success:
                    killed_count += 1
                    freed_mb += result.mem_freed_mb
                    log_entry = {
                        "ts": time.time(),
                        "pid": pid,
                        "name": proc.get("name", ""),
                        "mem_mb": proc.get("mem_mb", 0),
                        # [CN] "reason": f"自动终止:内存 {mem_pct:.0f}% / Swap {swap_pct:.0f}%",
                    }
                    with self.lock:
                        self.auto_kill_log.append(log_entry)
                        if len(self.auto_kill_log) > 20:
                            self.auto_kill_log.pop(0)
                    time.sleep(0.5)

            if killed_count:
                last_killed_time = time.time()
                print(f"[auto-kill] 自动终止 {killed_count} 个进程,释放约 {freed_mb:.0f} MB")
                # 抑制 Swap 告警 3 分钟,给系统时间释放 Swap
                self.alerter.suppress_swap_alert(180)

            time.sleep(15)

    def _block_loop(self):
        """黑名单拦截线程:有黑名单时每5秒扫描,无黑名单时休眠等待"""
        while True:
            if not self.blocked_processes:
                # 无黑名单时休眠,等待被唤醒(add_blocked_process 会 set 事件)
                self._block_event.wait(timeout=60)
                self._block_event.clear()
                continue

            with self.lock:
                blocked_names = set(self.blocked_processes)
                procs_snapshot = list(self.latest_processes)

            for proc in procs_snapshot:
                name = proc.get("name", "").lower()
                if name in blocked_names:
                    pid = proc["pid"]
                    result = kill_process(pid)
                    if result.success:
                        print(f"[block] 拦截黑名单进程 {name} (PID {pid})")
                        # TODO: Translate this log message

            time.sleep(5)

    def _scheduled_kill_loop(self):
        """定时终止线程:按固定间隔终止 safe 进程"""
        while True:
            time.sleep(30)
            if not self.scheduled_kill_enabled:
                continue

            interval_sec = self.scheduled_kill_interval * 60
            time.sleep(interval_sec)

            if not self.scheduled_kill_enabled:
                continue

            with self.lock:
                # 过滤掉白名单中的进程
                candidates = [
                    p for p in self.latest_processes
                    if p.get("risk") == "safe" and not self.whitelist.is_whitelisted(p)
                ]
            candidates.sort(key=lambda p: p.get("mem_mb", 0), reverse=True)

            killed_count = 0
            freed_mb = 0.0
            for proc in candidates[:3]:
                pid = proc["pid"]
                result = kill_process(pid)
                if result.success:
                    killed_count += 1
                    freed_mb += result.mem_freed_mb
                    log_entry = {
                        "ts": time.time(),
                        "pid": pid,
                        "name": proc.get("name", ""),
                        "mem_mb": proc.get("mem_mb", 0),
                        # [CN] "reason": f"定时终止(每 {self.scheduled_kill_interval} 分钟)",
                    }
                    with self.lock:
                        self.auto_kill_log.append(log_entry)
                        if len(self.auto_kill_log) > 20:
                            self.auto_kill_log.pop(0)
                    time.sleep(0.5)

            if killed_count:
                print(f"[scheduled-kill] Terminated {killed_count} processes, freed ~{freed_mb:.0f} MB")

    def _usage_refresh_loop(self):
        """Usage 轮询线程:每 10 分钟增量更新当天的 Claude 使用数据

        内存策略:
        - 只扫描今天修改过的 JSONL 文件
        - 增量解析:记录文件 offset,只读取新增内容
        - 峰值内存约 5-10MB(仅新增条目)
        """
        import gc
        import json
        from pathlib import Path
        from datetime import datetime
        from aigard.core.usage import (
            PricingManager, UsageCalculator, UsageAggregator, UsageCache
        )
        from aigard.core.usage.models import UsageEntry

        REFRESH_INTERVAL = 600  # 10 分钟

        # WaitingServiceLaunch
        time.sleep(10)

        while True:
            try:
                cache = UsageCache()
                today_str = datetime.now().strftime('%Y-%m-%d')

                # 首次:如果缓存完全为空,触发 API 端的全量加载
                if not cache.has_data():
                    print("[usage] 缓存为空,将在首次 API 请求时加载")
                    time.sleep(REFRESH_INTERVAL)
                    continue

                # 增量更新:只扫描今天修改过的 JSONL,且只读取新增内容
                claude_dir = Path.home() / ".claude" / "projects"
                today_entries = []

                if claude_dir.exists():
                    today_ts = datetime.now().replace(hour=0, minute=0, second=0).timestamp()

                    for project_dir in claude_dir.iterdir():
                        if not project_dir.is_dir():
                            continue
                        project_name = project_dir.name

                        for jsonl_file in project_dir.glob("*.jsonl"):
                            # 只处理今天修改过的文件
                            try:
                                if jsonl_file.stat().st_mtime < today_ts:
                                    continue
                            except OSError:
                                continue

                            file_key = str(jsonl_file)
                            last_offset = self._jsonl_offsets.get(file_key, 0)

                            try:
                                with open(jsonl_file, 'r', encoding='utf-8') as f:
                                    # 增量:跳到上次读取位置
                                    file_size = f.seek(0, 2)  # 先跳到文件末尾获取大小
                                    if last_offset > file_size:
                                        # 文件被截断/重写,重置 offset
                                        last_offset = 0
                                    f.seek(last_offset)

                                    for line in f:
                                        line = line.strip()
                                        if not line:
                                            continue
                                        try:
                                            data = json.loads(line)
                                            if data.get('type') != 'assistant':
                                                continue
                                            ts_str = data.get('timestamp', '')
                                            if not ts_str or not ts_str.startswith(today_str):
                                                continue
                                            msg = data.get('message', {})
                                            usage = msg.get('usage')
                                            if not usage:
                                                continue

                                            entry = UsageEntry(
                                                timestamp=datetime.strptime(ts_str[:19], '%Y-%m-%dT%H:%M:%S'),
                                                model=msg.get('model', 'unknown'),
                                                input_tokens=usage.get('input_tokens', 0),
                                                output_tokens=usage.get('output_tokens', 0),
                                                cache_creation_tokens=usage.get('cache_creation_input_tokens', 0),
                                                cache_read_tokens=usage.get('cache_read_input_tokens', 0),
                                                cost=0.0,
                                                project=project_name,
                                                session_id=jsonl_file.stem
                                            )
                                            today_entries.append(entry)
                                        except (json.JSONDecodeError, ValueError, KeyError):
                                            continue

                                    # 记录新的读取位置
                                    self._jsonl_offsets[file_key] = f.tell()
                            except Exception:
                                # 文件被删除/截断,重置 offset
                                self._jsonl_offsets.pop(file_key, None)
                                continue

                if today_entries:
                    pricing = PricingManager()
                    calc = UsageCalculator(pricing)
                    agg = UsageAggregator(calc)

                    daily = agg.aggregate_by_day(today_entries)
                    hourly = agg.aggregate_by_hour(today_entries)

                    daily_data = [self._summary_to_dict(s, 'daily') for s in daily]
                    hourly_data = [self._summary_to_dict(s, 'hourly') for s in hourly]

                    cache.save_daily(daily_data)
                    cache.save_hourly(hourly_data)
                    cache.set_last_update_time(datetime.now().isoformat())

                    # 立即释放
                    del today_entries, daily, hourly, daily_data, hourly_data

                # 更新菜单栏今日统计
                today_summary = cache.get_summary(
                    start_date=today_str,
                    end_date=today_str
                )
                with self.lock:
                    self._today_usage = today_summary

                gc.collect()

            except Exception as e:
                print(f"[usage] UpdateFailure: {e}")

            time.sleep(REFRESH_INTERVAL)

    def _summary_to_dict(self, summary, kind):
        """将 DailySummary/HourlySummary 转为字典"""
        base = {
            'input_tokens': summary.input_tokens,
            'output_tokens': summary.output_tokens,
            'cache_creation_tokens': summary.cache_creation_tokens,
            'cache_read_tokens': summary.cache_read_tokens,
            'total_tokens': summary.total_tokens,
            'total_cost': summary.total_cost,
            'models_used': summary.models_used,
            'request_count': getattr(summary, 'request_count', 0),  # [CN] 使用数据模型的 request_count
        }
        if kind == 'daily':
            base['date'] = summary.date
            base['model_breakdowns'] = [
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
                for mb in summary.model_breakdowns
            ]
        else:
            base['hour'] = summary.hour
        return base

    def get_today_usage(self):
        """获取今日使用统计(供菜单栏调用)"""
        with self.lock:
            return getattr(self, '_today_usage', None)
