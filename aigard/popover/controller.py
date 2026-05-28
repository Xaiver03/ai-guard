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
        print("=== PopoverViewController.loadView() 被调用 ===")
        # 创建主容器（尺寸：360×500）
        container = NSView.alloc().initWithFrame_(
            ((0, 0), (360, 500))
        )
        print(f"✅ 容器创建成功: {container}, frame: {container.frame()}")

        # 使用 view_builder 构建 UI
        from .view_builder import build_popover_ui
        print("开始构建 UI...")
        self.metrics_labels, self.progress_bars = build_popover_ui(
            container, self
        )
        print(f"✅ UI 构建完成, labels: {len(self.metrics_labels)}, bars: {len(self.progress_bars)}")

        self.setView_(container)
        print(f"✅ setView 完成, view: {self.view()}")

    def update_metrics(self):
        """更新指标数据（从 threads.history.latest 读取）"""
        from .view_builder import _semantic_color, _format_gb

        latest = self.threads.history.latest
        if not latest:
            return

        # 更新各卡片的主要数值和详细信息
        metric_details = {
            'cpu': ('cpu_percent', None, None),
            'mem': ('mem_percent', 'mem_used_gb', 'mem_total_gb'),
            'swap': ('swap_percent', 'swap_used_gb', 'swap_total_gb'),
            'disk': ('disk_percent', 'disk_used_gb', 'disk_total_gb'),
        }

        for key, (pct_key, used_key, total_key) in metric_details.items():
            value = latest.get(pct_key, 0)

            # 更新主要数值（大号百分比）
            if key in self.metrics_labels:
                lbl = self.metrics_labels[key]
                lbl.setStringValue_(f"{value:.0f}%")
                lbl.setTextColor_(_semantic_color(value))

            # 更新详细信息（used / total GB）
            detail_key = f'{key}_detail'
            if detail_key in self.metrics_labels and used_key and total_key:
                used = latest.get(used_key, 0)
                total = latest.get(total_key, 0)
                self.metrics_labels[detail_key].setStringValue_(_format_gb(used, total))

        # 更新磁盘 I/O 速度
        if 'disk_io' in self.metrics_labels:
            read_kbs = latest.get('disk_read_kbs', 0)
            write_kbs = latest.get('disk_write_kbs', 0)
            self.metrics_labels['disk_io'].setStringValue_(f"R: {read_kbs:.0f} KB/s  W: {write_kbs:.0f} KB/s")

        # 更新标题栏的内存徽章
        if 'mem_badge' in self.metrics_labels:
            mem = latest.get('mem_percent', 0)
            self.metrics_labels['mem_badge'].setStringValue_(f"{mem:.0f}%")
            self.metrics_labels['mem_badge'].setTextColor_(_semantic_color(mem))

    def update_usage(self):
        """更新 Claude 使用统计"""
        usage = self.threads.get_today_usage()
        if usage and usage.get('total_tokens', 0) > 0:
            tokens = usage['total_tokens']
            cost = usage.get('total_cost', 0)
            requests = usage.get('request_count', 0) or usage.get('total_requests', 0)  # 兼容两种字段名

            # 格式化 Token 显示
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
        else:
            if 'usage_token' in self.metrics_labels:
                self.metrics_labels['usage_token'].setStringValue_("Token: 0")
            if 'usage_cost' in self.metrics_labels:
                self.metrics_labels['usage_cost'].setStringValue_("费用: $0.00")
            if 'usage_requests' in self.metrics_labels:
                self.metrics_labels['usage_requests'].setStringValue_("请求: 0 次")

    def update_autokill_button(self):
        """更新自动终止按钮文本"""
        state = self.threads.autokill_enabled
        if 'autokill_btn' in self.metrics_labels:
            self.metrics_labels['autokill_btn'].setTitle_(f"自动: {'开' if state else '关'}")

    # ── 按钮回调方法 ──────────────────────────────────────────

    @objc.selector
    def killSafeProcesses_(self, sender):
        """一键终止安全进程"""
        print(f"=== killSafeProcesses_ 被调用 ===")
        try:
            import os
            from aigard.core import kill_process

            # 获取当前进程 PID (自我保护)
            current_pid = os.getpid()
            print(f"当前应用 PID: {current_pid}")

            print(f"threads: {self.threads}")
            if not self.threads:
                msg = "后台服务未启动"
                print(f"❌ {msg}")
                self._send_notification("AI Guard", msg)
                return

            print(f"threads.lock: {self.threads.lock}")
            print(f"threads.latest_processes: {hasattr(self.threads, 'latest_processes')}")

            with self.threads.lock:
                # 过滤掉当前进程 (自我保护)
                safe_procs = [
                    p for p in self.threads.latest_processes
                    if p.get("risk") == "safe" and p.get("pid") != current_pid
                ]

            print(f"找到 {len(safe_procs)} 个安全进程 (已排除当前进程)")

            if not safe_procs:
                msg = "当前没有可安全终止的进程"
                print(f"⚠️ {msg}")
                self._send_notification("AI Guard", msg)
                return

            killed = 0
            total_freed = 0.0
            for proc in safe_procs:
                pid = proc['pid']
                name = proc.get('name', 'unknown')
                print(f"终止进程: {pid} - {name}")
                r = kill_process(pid)
                if r.success:
                    killed += 1
                    total_freed += r.mem_freed_mb
                    print(f"  ✅ 已终止,释放 {r.mem_freed_mb:.0f} MB")
                else:
                    print(f"  ❌ 终止失败")

            msg = f"已终止 {killed} 个进程，释放 {total_freed:.0f} MB"
            print(f"✅ {msg}")
            self._send_notification("AI Guard", msg)
        except Exception as e:
            msg = f"终止进程失败: {str(e)}"
            print(f"❌ {msg}")
            import traceback
            traceback.print_exc()
            self._send_notification("AI Guard", msg)

    @objc.selector
    def toggleAutokill_(self, sender):
        """切换自动终止开关"""
        print(f"=== toggleAutokill_ 被调用 ===")
        with self.threads.lock:
            self.threads.autokill_enabled = not self.threads.autokill_enabled
            state = self.threads.autokill_enabled

        # 更新按钮文本
        sender.setTitle_(f"自动: {'开' if state else '关'}")

        # 反馈
        status = "已开启" if state else "已关闭"
        msg = f"自动终止{status}"
        print(f"✅ {msg}")
        self._show_status(msg)
        self._send_notification("AI Guard", msg)

    @objc.selector
    def openDashboard_(self, sender):
        """打开完整监控面板 - 使用原生窗口"""
        print(f"=== openDashboard_ 被调用 ===")
        try:
            from aigard.window_manager import DashboardWindow
            dashboard = DashboardWindow.get_instance(self.server_url)
            dashboard.show()
            print("✅ Dashboard 窗口已打开")
            self._send_notification("AI Guard", "监控面板已打开")
        except Exception as e:
            print(f"❌ 打开 Dashboard 失败: {e}")
            import traceback
            traceback.print_exc()
            self._send_notification("AI Guard", f"打开失败: {str(e)}")

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
