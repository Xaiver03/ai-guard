"""
# [CN] PopoverViewController - Popover 内容视图控制器(原生 AppKit 控件)
"""
import objc
import webbrowser
import requests
from AppKit import NSViewController, NSView, NSUserNotificationCenter, NSUserNotification
from Foundation import NSRect, NSSize


class PopoverViewController(NSViewController):
    # [CN] """Popover 内容视图控制器(原生 AppKit 控件)"""

    def init(self):
        # [CN] """初始化方法(ObjC 风格)"""
        self = objc.super(PopoverViewController, self).init()
        if self is None:
            return None

        self.threads = None
        self.server_url = "http://127.0.0.1:8765"
        self.metrics_labels = {}  # [CN] 存储需要更新的标签引用
        self.progress_bars = {}   # [CN] 存储进度条引用
        return self

    def initWithThreadsManager_serverUrl_(self, threads_manager, server_url):
        """CustomInitializeMethod"""
        self = self.init()
        if self is None:
            return None

        self.threads = threads_manager
        self.server_url = server_url
        return self

    def loadView(self):
        # [CN] """构建原生 NSView 布局"""
        # [CN] print("=== PopoverViewController.loadView() 被调用 ===")
        # TODO: Translate this log message
        # [CN] 创建主容器(尺寸:360×500)
        container = NSView.alloc().initWithFrame_(
            ((0, 0), (360, 500))
        )
        # [CN] print(f"✅ 容器创建成功: {container}, frame: {container.frame()}")
        # TODO: Translate this log message

        # [CN] 使用 view_builder 构建 UI
        from .view_builder import build_popover_ui
        print("StartBuilding UI...")
        self.metrics_labels, self.progress_bars = build_popover_ui(
            container, self
        )
        print(f"✅ UI BuildingFinish, labels: {len(self.metrics_labels)}, bars: {len(self.progress_bars)}")

        self.setView_(container)
        print(f"✅ setView Finish, view: {self.view()}")

    def update_metrics(self):
        # [CN] """更新指标数据(从 threads.history.latest 读取)"""
        from .view_builder import _semantic_color, _format_gb

        latest = self.threads.history.latest
        if not latest:
            return

        # [CN] # 更新各卡片的主要数值和详细信息
        metric_details = {
            'cpu': ('cpu_percent', None, None),
            'mem': ('mem_percent', 'mem_used_gb', 'mem_total_gb'),
            'swap': ('swap_percent', 'swap_used_gb', 'swap_total_gb'),
            'disk': ('disk_percent', 'disk_used_gb', 'disk_total_gb'),
        }

        for key, (pct_key, used_key, total_key) in metric_details.items():
            value = latest.get(pct_key, 0)

            # [CN] # 更新主要数值(大号百分比)
            if key in self.metrics_labels:
                lbl = self.metrics_labels[key]
                lbl.setStringValue_(f"{value:.0f}%")
                lbl.setTextColor_(_semantic_color(value))

            # [CN] # 更新进度条
            if key in self.progress_bars:
                bar = self.progress_bars[key]
                bar.setDoubleValue_(value)

            # UpdateVerboseInfo(used / total GB)
            detail_key = f'{key}_detail'
            if detail_key in self.metrics_labels and used_key and total_key:
                used = latest.get(used_key, 0)
                total = latest.get(total_key, 0)
                self.metrics_labels[detail_key].setStringValue_(_format_gb(used, total))

        # [CN] # 更新磁盘 I/O 速度
        if 'disk_io' in self.metrics_labels:
            read_kbs = latest.get('disk_read_kbs', 0)
            write_kbs = latest.get('disk_write_kbs', 0)
            self.metrics_labels['disk_io'].setStringValue_(f"R: {read_kbs:.0f} KB/s  W: {write_kbs:.0f} KB/s")

        # [CN] # 更新标题栏的内存徽章
        if 'mem_badge' in self.metrics_labels:
            mem = latest.get('mem_percent', 0)
            self.metrics_labels['mem_badge'].setStringValue_(f"{mem:.0f}%")
            self.metrics_labels['mem_badge'].setTextColor_(_semantic_color(mem))

    def update_usage(self):
        # [CN] """更新 Claude 使用统计"""
        usage = self.threads.get_today_usage()
        if usage and usage.get('total_tokens', 0) > 0:
            tokens = usage['total_tokens']
            cost = usage.get('total_cost', 0)
            requests = usage.get('request_count', 0) or usage.get('total_requests', 0)  # [CN] 兼容两种字段名

            # [CN] 格式化 Token 显示
            if tokens >= 1_000_000:
                token_str = f"{tokens/1_000_000:.1f}M"
            elif tokens >= 1000:
                token_str = f"{tokens/1000:.0f}K"
            else:
                token_str = str(tokens)

            if 'usage_token' in self.metrics_labels:
                self.metrics_labels['usage_token'].setStringValue_(f"Token: {token_str}")
            if 'usage_cost' in self.metrics_labels:
                self.metrics_labels['usage_cost'].setStringValue_(f"费用: ${cost:.2f}")
            if 'usage_requests' in self.metrics_labels:
                self.metrics_labels['usage_requests'].setStringValue_(f"请求: {requests} 次")

            # [CN] 更新折线图
            if 'token_chart' in self.metrics_labels:
                chart_data = self._get_token_history()
                self.metrics_labels['token_chart'].setData_(chart_data)
        else:
            if 'usage_token' in self.metrics_labels:
                self.metrics_labels['usage_token'].setStringValue_("Token: 0")
            if 'usage_cost' in self.metrics_labels:
                self.metrics_labels['usage_cost'].setStringValue_("费用: $0.00")
            if 'usage_requests' in self.metrics_labels:
                self.metrics_labels['usage_requests'].setStringValue_("请求: 0 次")

    def _get_token_history(self):
        # [CN] """获取最近 7 天的 Token 历史数据"""
        try:
            import requests
            response = requests.get(f"{self.server_url}/api/usage/daily?preset=last7days", timeout=2)
            if response.status_code == 200:
                daily_data = response.json()
                # [CN] # 转换为折线图数据格式 [(x, y), ...]
                chart_data = [(i, d.get('total_tokens', 0)) for i, d in enumerate(daily_data[-7:])]
                return chart_data
        except Exception as e:
            print(f"Get Token HistoryFailure: {e}")
        return []

    def update_autokill_button(self):
        # [CN] """更新自动终止按钮文本"""
        state = self.threads.autokill_enabled
        if 'autokill_btn' in self.metrics_labels:
            self.metrics_labels['autokill_btn'].setTitle_(f"自动: {'开' if state else '关'}")

    # [CN] ── 按钮回调方法 ──────────────────────────────────────────

    @objc.selector
    def killSafeProcesses_(self, sender):
        # [CN] """一键终止安全进程"""
        # [CN] print(f"=== killSafeProcesses_ 被调用 ===")
        try:
            import os
            from aigard.core import kill_process

            # [CN] # 获取当前进程 PID (自我保护)
            current_pid = os.getpid()
            parent_pid = os.getppid()
            # [CN] print(f"当前应用 PID: {current_pid}")

            print(f"threads: {self.threads}")
            if not self.threads:
                # [CN] msg = "后台服务未启动"
                print(f"❌ {msg}")
                self._send_notification("AI Guard", msg)
                return

            print(f"threads.lock: {self.threads.lock}")
            print(f"threads.latest_processes: {hasattr(self.threads, 'latest_processes')}")

            with self.threads.lock:
                # [CN] # 过滤掉当前进程和父进程 (自我保护)
                safe_procs = [
                    p for p in self.threads.latest_processes
                    if p.get("risk") == "safe" and p.get("pid") not in (current_pid, parent_pid)
                ]

            # [CN] print(f"找到 {len(safe_procs)} 个安全进程 (已排除当前进程)")

            if not safe_procs:
                # [CN] msg = "当前没有可安全终止的进程"
                print(f"⚠️ {msg}")
                self._send_notification("AI Guard", msg)
                return

            killed = 0
            total_freed = 0.0
            for proc in safe_procs:
                pid = proc['pid']
                name = proc.get('name', 'unknown')
                print(f"TerminateProcess: {pid} - {name}")
                r = kill_process(pid)
                if r.success:
                    killed += 1
                    total_freed += r.mem_freed_mb
                    # [CN] print(f"  ✅ 已终止,释放 {r.mem_freed_mb:.0f} MB")
                else:
                    print(f"  ❌ TerminateFailure")

            # [CN] msg = f"已终止 {killed} 个进程,释放 {total_freed:.0f} MB"
            print(f"✅ {msg}")
            self._send_notification("AI Guard", msg)
        except Exception as e:
            msg = f"TerminateProcessFailure: {str(e)}"
            print(f"❌ {msg}")
            import traceback
            traceback.print_exc()
            self._send_notification("AI Guard", msg)

    @objc.selector
    def toggleAutokill_(self, sender):
        # [CN] """切换自动终止开关"""
        # [CN] print(f"=== toggleAutokill_ 被调用 ===")
        # TODO: Translate this log message
        with self.threads.lock:
            self.threads.autokill_enabled = not self.threads.autokill_enabled
            state = self.threads.autokill_enabled

        # [CN] 更新按钮文本
        sender.setTitle_(f"自动: {'开' if state else '关'}")

        # [CN] 反馈
        status = "已开启" if state else "已关闭"
        msg = f"自动终止{status}"
        print(f"✅ {msg}")
        self._show_status(msg)
        self._send_notification("AI Guard", msg)

    @objc.selector
    def openDashboard_(self, sender):
        # [CN] """打开完整监控面板 - 使用原生窗口"""
        # [CN] print(f"=== openDashboard_ 被调用 ===")
        try:
            from aigard.window_manager import DashboardWindow
            dashboard = DashboardWindow.get_instance(self.server_url)
            dashboard.show()
            # [CN] print("✅ Dashboard 窗口已打开")
            # [CN] self._send_notification("AI Guard", "监控面板已打开")
        except Exception as e:
            # [CN] print(f"❌ 打开 Dashboard 失败: {e}")
            import traceback
            traceback.print_exc()
            # [CN] self._send_notification("AI Guard", f"打开失败: {str(e)}")

    @objc.selector
    def refreshUsage_(self, sender):
        # [CN] """手动刷新 Claude 使用统计"""
        self._show_status("刷新中...")
        try:
            resp = requests.post(f"{self.server_url}/api/usage/refresh", timeout=30)
            if resp.status_code == 200:
                self.update_usage()
                self._show_status("使用统计已刷新")
            else:
                self._show_status("刷新失败,请稍后重试", is_error=True)
        except Exception as e:
            self._show_status(f"刷新失败: {str(e)}", is_error=True)

    @objc.selector
    def quitApp_(self, sender):
        """Exit AI Guard"""
        import rumps
        rumps.quit_application()

    def _show_status(self, message, is_error=False):
        # [CN] """在 Popover 底部状态栏显示反馈消息(3 秒后自动消失)"""
        from AppKit import NSColor, NSFont
        import threading

        if 'status' not in self.metrics_labels:
            return

        label = self.metrics_labels['status']
        color = NSColor.systemRedColor() if is_error else NSColor.systemGreenColor()
        label.setTextColor_(color)
        label.setFont_(NSFont.systemFontOfSize_weight_(11, 0.5))
        label.setStringValue_(message)

        # [CN] 3 秒后清空(在主线程执行)
        def _clear():
            from AppKit import NSColor
            if label.stringValue() == message:  # [CN] 防止清掉更新的消息
                label.setStringValue_("")
        threading.Timer(3.0, _clear).start()

    def _send_notification(self, title, message):
        # [CN] """发送 macOS 系统通知"""
        try:
            import subprocess
            # [CN] # 使用 osascript 发送通知 (兼容所有 macOS 版本)
            script = f'display notification "{message}" with title "{title}"'
            subprocess.run(['osascript', '-e', script], check=False, capture_output=True)
            # [CN] print(f"✅ 通知已发送: {title} - {message}")
        except Exception as e:
            print(f"❌ NotificationSendFailure: {e}")
            # [CN] pass  # 系统通知失败不影响功能
