"""
PopoverViewController - Popover 内容视图控制器（原生 AppKit 控件）
"""
import objc
import webbrowser
import requests
from AppKit import NSViewController, NSView, NSUserNotificationCenter, NSUserNotification
from Foundation import NSRect, NSSize


class PopoverViewController(NSViewController):
    """Popover 内容视图控制器（原生 AppKit 控件）"""

    def init(self):
        """初始化方法（ObjC 风格）"""
        self = objc.super(PopoverViewController, self).init()
        if self is None:
            return None

        self.threads = None
        self.server_url = "http://127.0.0.1:8765"
        self.metrics_labels = {}  # 存储需要更新的标签引用
        self.progress_bars = {}   # 存储进度条引用
        return self

    def initWithThreadsManager_serverUrl_(self, threads_manager, server_url):
        """自定义初始化方法"""
        self = self.init()
        if self is None:
            return None

        self.threads = threads_manager
        self.server_url = server_url
        return self

    def loadView(self):
        """构建原生 NSView 布局"""
        # 创建主容器
        container = NSView.alloc().initWithFrame_(
            ((0, 0), (300, 480))
        )

        # 使用 view_builder 构建 UI
        from .view_builder import build_popover_ui
        self.metrics_labels, self.progress_bars = build_popover_ui(
            container, self
        )

        self.setView_(container)

    def update_metrics(self):
        """更新指标数据（从 threads.history.latest 读取）"""
        from .view_builder import _semantic_color, _format_gb

        latest = self.threads.history.latest
        if not latest:
            return

        # 更新进度条、百分比和详细数值
        metric_details = {
            'cpu': ('cpu_percent', None, None),
            'mem': ('mem_percent', 'mem_used_gb', 'mem_total_gb'),
            'swap': ('swap_percent', 'swap_used_gb', 'swap_total_gb'),
            'disk': ('disk_percent', 'disk_used_gb', 'disk_total_gb'),
        }

        for key, (pct_key, used_key, total_key) in metric_details.items():
            value = latest.get(pct_key, 0)

            # 更新进度条颜色和值
            if key in self.progress_bars:
                bar = self.progress_bars[key]
                bar.setDoubleValue_(value)

            # 更新百分比标签和颜色
            if key in self.metrics_labels:
                lbl = self.metrics_labels[key]
                lbl.setStringValue_(f"{value:.0f}%")
                lbl.setTextColor_(_semantic_color(value))

            # 更新详细数值（used / total GB）
            detail_key = f'{key}_detail'
            if detail_key in self.metrics_labels and used_key and total_key:
                used = latest.get(used_key, 0)
                total = latest.get(total_key, 0)
                self.metrics_labels[detail_key].setStringValue_(_format_gb(used, total))

    def update_usage(self):
        """更新 Claude 使用统计"""
        usage = self.threads.get_today_usage()
        if usage and usage.get('total_tokens', 0) > 0:
            tokens = usage['total_tokens']
            cost = usage.get('total_cost', 0)
            # 格式化显示
            if tokens >= 1_000_000:
                token_str = f"{tokens/1_000_000:.1f}M"
            elif tokens >= 1000:
                token_str = f"{tokens/1000:.0f}K"
            else:
                token_str = str(tokens)

            if 'usage' in self.metrics_labels:
                self.metrics_labels['usage'].setStringValue_(
                    f"Token {token_str} · ${cost:.2f}"
                )
        else:
            if 'usage' in self.metrics_labels:
                self.metrics_labels['usage'].setStringValue_("Token 0 · $0.00")

    def update_autokill_button(self):
        """更新自动终止按钮文本"""
        state = self.threads.autokill_enabled
        if 'autokill_btn' in self.metrics_labels:
            self.metrics_labels['autokill_btn'].setTitle_(f"自动: {'开' if state else '关'}")

    # ── 按钮回调方法 ──────────────────────────────────────────

    @objc.selector
    def killSafeProcesses_(self, sender):
        """一键终止安全进程"""
        from aigard.core import kill_process

        with self.threads.lock:
            safe_procs = [p for p in self.threads.latest_processes if p.get("risk") == "safe"]

        if not safe_procs:
            self._show_status("当前没有可安全终止的进程")
            return

        killed = 0
        total_freed = 0.0
        for proc in safe_procs:
            r = kill_process(proc["pid"])
            if r.success:
                killed += 1
                total_freed += r.mem_freed_mb

        msg = f"已终止 {killed} 个进程，释放 {total_freed:.0f} MB"
        self._show_status(msg)
        self._send_notification("AI Guard", msg)

    @objc.selector
    def toggleAutokill_(self, sender):
        """切换自动终止开关"""
        with self.threads.lock:
            self.threads.autokill_enabled = not self.threads.autokill_enabled
            state = self.threads.autokill_enabled

        # 更新按钮文本
        sender.setTitle_(f"自动: {'开' if state else '关'}")

        # 反馈
        status = "已开启" if state else "已关闭"
        self._show_status(f"自动终止{status}")

    @objc.selector
    def openDashboard_(self, sender):
        """打开完整监控面板"""
        webbrowser.open(self.server_url)

    @objc.selector
    def refreshUsage_(self, sender):
        """手动刷新 Claude 使用统计"""
        self._show_status("刷新中...")
        try:
            resp = requests.post(f"{self.server_url}/api/usage/refresh", timeout=30)
            if resp.status_code == 200:
                self.update_usage()
                self._show_status("使用统计已刷新")
            else:
                self._show_status("刷新失败，请稍后重试", is_error=True)
        except Exception as e:
            self._show_status(f"刷新失败: {str(e)}", is_error=True)

    @objc.selector
    def quitApp_(self, sender):
        """退出 AI Guard"""
        import rumps
        rumps.quit_application()

    def _show_status(self, message, is_error=False):
        """在 Popover 底部状态栏显示反馈消息（3 秒后自动消失）"""
        from AppKit import NSColor, NSFont
        import threading

        if 'status' not in self.metrics_labels:
            return

        label = self.metrics_labels['status']
        color = NSColor.systemRedColor() if is_error else NSColor.systemGreenColor()
        label.setTextColor_(color)
        label.setFont_(NSFont.systemFontOfSize_weight_(11, 0.5))
        label.setStringValue_(message)

        # 3 秒后清空（在主线程执行）
        def _clear():
            from AppKit import NSColor
            if label.stringValue() == message:  # 防止清掉更新的消息
                label.setStringValue_("")
        threading.Timer(3.0, _clear).start()

    def _send_notification(self, title, message):
        """发送 macOS 系统通知（作为补充反馈）"""
        try:
            notification = NSUserNotification.alloc().init()
            notification.setTitle_(title)
            notification.setInformativeText_(message)
            NSUserNotificationCenter.defaultUserNotificationCenter().deliverNotification_(notification)
        except Exception:
            pass  # 系统通知失败不影响功能
