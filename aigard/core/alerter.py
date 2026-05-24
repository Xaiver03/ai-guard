"""alerter.py — 分级告警（macOS 原生通知）"""

import subprocess
import time


class Alerter:
    def __init__(self, cfg: dict):
        self.mem_warn = cfg.get("mem_warn", 80)
        self.mem_crit = cfg.get("mem_crit", 90)
        self.swap_warn = cfg.get("swap_warn", 50)
        self.swap_crit = cfg.get("swap_crit", 80)
        self.disk_free_warn_gb = cfg.get("disk_free_warn_gb", 20)
        self.disk_free_crit_gb = cfg.get("disk_free_crit_gb", 10)
        self.cooldown_sec = cfg.get("cooldown_sec", 60)
        # Swap 告警使用更长的冷却时间（默认 5 分钟），因为 Swap 释放较慢
        self.swap_cooldown_sec = cfg.get("swap_cooldown_sec", 300)
        self._last_notify: dict[str, float] = {}
        # 自动清理后的 Swap 告警抑制时间戳
        self._swap_suppress_until = 0.0

    def _can_notify(self, key: str) -> bool:
        now = time.time()
        last = self._last_notify.get(key, 0)
        # Swap 相关告警使用更长的冷却时间
        cooldown = self.swap_cooldown_sec if 'swap' in key.lower() else self.cooldown_sec
        if now - last >= cooldown:
            self._last_notify[key] = now
            return True
        return False

    def suppress_swap_alert(self, duration_sec: int = 180):
        """抑制 Swap 告警一段时间（默认 3 分钟）
        用于自动清理后，给系统时间释放 Swap
        """
        self._swap_suppress_until = time.time() + duration_sec

    def _notify(self, title: str, body: str):
        """发送 macOS 通知，优先使用 rumps（权限更干净），fallback osascript"""
        try:
            import rumps
            rumps.notification(title=title, subtitle="", message=body)
            return
        except ImportError:
            pass
        except Exception:
            pass
        # fallback to osascript
        script = f'display notification "{body}" with title "{title}" sound name "Funk"'
        try:
            subprocess.run(["osascript", "-e", script], check=False, timeout=5)
        except Exception:
            pass

    def check(self, metrics: dict) -> str:
        """检查指标，返回告警等级: normal / warn / crit"""
        level = "normal"
        reasons = []

        mem_pct = metrics.get("mem_percent", 0)
        swap_pct = metrics.get("swap_percent", 0)
        disk_free = metrics.get("disk_free_gb", 999)

        # 检查 Swap 是否在抑制期内
        swap_suppressed = time.time() < self._swap_suppress_until

        # 判断 crit
        if mem_pct >= self.mem_crit:
            level = "crit"
            reasons.append(f"内存 {mem_pct:.0f}%")
        if not swap_suppressed and swap_pct >= self.swap_crit:
            level = "crit"
            reasons.append(f"Swap {swap_pct:.0f}%")
        if disk_free <= self.disk_free_crit_gb:
            level = "crit"
            reasons.append(f"磁盘仅剩 {disk_free:.1f}GB")

        # 判断 warn（未达 crit）
        if level == "normal":
            if mem_pct >= self.mem_warn:
                level = "warn"
                reasons.append(f"内存 {mem_pct:.0f}%")
            if not swap_suppressed and swap_pct >= self.swap_warn:
                level = "warn"
                reasons.append(f"Swap {swap_pct:.0f}%")
            if disk_free <= self.disk_free_warn_gb:
                level = "warn"
                reasons.append(f"磁盘仅剩 {disk_free:.1f}GB")

        if level == "crit" and self._can_notify("crit"):
            self._notify(
                "AI Guard — 危险",
                "，".join(reasons) + "，建议立即暂停 AI Agent"
            )
        elif level == "warn" and self._can_notify("warn"):
            self._notify(
                "AI Guard — 警告",
                "，".join(reasons) + "，请注意资源压力"
            )

        return level
