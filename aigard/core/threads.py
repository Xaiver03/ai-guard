"""
后台线程模块 - 监控、自动终止、黑名单拦截、定时终止
"""

import time
import threading
from dataclasses import asdict

from aigard.core import (
    collect_metrics, collect_ai_processes, advise_list,
    kill_process, Alerter, MetricsHistory
)


class BackgroundThreads:
    """管理所有后台线程"""

    def __init__(self, config: dict, history: MetricsHistory, alerter: Alerter):
        self.config = config
        self.history = history
        self.alerter = alerter

        # 共享状态
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

        # 线程对象
        self._threads = []

    def start_all(self):
        """启动所有后台线程"""
        self._threads = [
            threading.Thread(target=self._monitor_loop, daemon=True),
            threading.Thread(target=self._auto_kill_loop, daemon=True),
            threading.Thread(target=self._block_loop, daemon=True),
            threading.Thread(target=self._scheduled_kill_loop, daemon=True),
        ]
        for t in self._threads:
            t.start()

    def _monitor_loop(self):
        """监控线程：采集指标和进程列表"""
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
        """自动终止线程：内存超阈值时终止 safe 进程"""
        last_killed_time = 0.0

        while True:
            time.sleep(5)
            if not self.autokill_enabled:
                continue

            with self.settings_lock:
                ak = self.settings.get("auto_kill", {})
            mem_trigger = ak.get("mem_trigger_pct", 85)
            swap_trigger = ak.get("swap_trigger_pct", 75)
            target_mem = ak.get("target_mem_pct", 70)
            cooldown = ak.get("cooldown_sec", 120)

            latest = self.history.latest
            if not latest:
                continue

            mem_pct = latest.get("mem_percent", 0)
            swap_pct = latest.get("swap_percent", 0)

            if mem_pct < mem_trigger and swap_pct < swap_trigger:
                continue
            if time.time() - last_killed_time < cooldown:
                continue

            with self.lock:
                candidates = [p for p in self.latest_processes if p.get("risk") == "safe"]
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
                        "reason": f"自动终止：内存 {mem_pct:.0f}% / Swap {swap_pct:.0f}%",
                    }
                    with self.lock:
                        self.auto_kill_log.append(log_entry)
                        if len(self.auto_kill_log) > 20:
                            self.auto_kill_log.pop(0)
                    time.sleep(0.5)

            if killed_count:
                last_killed_time = time.time()
                print(f"[auto-kill] 自动终止 {killed_count} 个进程，释放约 {freed_mb:.0f} MB")

    def _block_loop(self):
        """黑名单拦截线程：每秒扫描黑名单进程并终止"""
        while True:
            time.sleep(1)
            if not self.blocked_processes:
                continue

            with self.lock:
                blocked_names = set(self.blocked_processes)

            for proc in self.latest_processes:
                name = proc.get("name", "").lower()
                if name in blocked_names:
                    pid = proc["pid"]
                    result = kill_process(pid)
                    if result.success:
                        print(f"[block] 拦截黑名单进程 {name} (PID {pid})")

    def _scheduled_kill_loop(self):
        """定时终止线程：按固定间隔终止 safe 进程"""
        while True:
            time.sleep(30)
            if not self.scheduled_kill_enabled:
                continue

            interval_sec = self.scheduled_kill_interval * 60
            time.sleep(interval_sec)

            if not self.scheduled_kill_enabled:
                continue

            with self.lock:
                candidates = [p for p in self.latest_processes if p.get("risk") == "safe"]
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
                        "reason": f"定时终止（每 {self.scheduled_kill_interval} 分钟）",
                    }
                    with self.lock:
                        self.auto_kill_log.append(log_entry)
                        if len(self.auto_kill_log) > 20:
                            self.auto_kill_log.pop(0)
                    time.sleep(0.5)

            if killed_count:
                print(f"[scheduled-kill] 定时终止 {killed_count} 个进程，释放约 {freed_mb:.0f} MB")
