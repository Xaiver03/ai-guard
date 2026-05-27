"""app_native.py — 原生 macOS 菜单栏应用（纯 PyObjC，支持 Popover）

运行方式：
    python app_native.py          # 开发模式
    open "dist/AI Guard.app"      # 打包后
"""

import os
import sys
import threading
import webbrowser
from pathlib import Path

import objc
from Foundation import NSObject, NSTimer, NSMakeRect, NSURL, NSURLRequest
from AppKit import (
    NSApplication, NSStatusBar, NSVariableStatusItemLength,
    NSPopover, NSViewController, NSVisualEffectView,
    NSVisualEffectMaterialPopover, NSVisualEffectBlendingModeBehindWindow,
    NSMenu, NSMenuItem, NSApp, NSImage
)
from WebKit import WKWebView

# 禁止 main.py 的 on_startup 自动打开浏览器
os.environ["AIGARD_NO_BROWSER"] = "1"

# 确保能 import 到同级的 main.py
# 打包后 main.py 在 Resources 目录下
if getattr(sys, 'frozen', False):
    # 打包后的路径
    bundle_dir = Path(sys._MEIPASS if hasattr(sys, '_MEIPASS') else sys.executable).parent
    if (bundle_dir / 'Resources').exists():
        sys.path.insert(0, str(bundle_dir / 'Resources'))
    else:
        sys.path.insert(0, str(bundle_dir))
else:
    # 开发模式
    sys.path.insert(0, str(Path(__file__).parent))

import main as _main_mod


class PopoverViewController(NSViewController):
    """Popover 视图控制器"""

    def init(self):
        self = objc.super(PopoverViewController, self).init()
        if self is None:
            return None
        self.webview = None
        self.url = "http://127.0.0.1:8765/popover.html"
        return self

    def loadView(self):
        """创建视图"""
        # 创建毛玻璃背景视图
        effect_view = NSVisualEffectView.alloc().initWithFrame_(
            NSMakeRect(0, 0, 360, 400)
        )
        effect_view.setMaterial_(NSVisualEffectMaterialPopover)
        effect_view.setBlendingMode_(NSVisualEffectBlendingModeBehindWindow)
        effect_view.setState_(1)  # NSVisualEffectStateActive

        # 创建 WebView
        self.webview = WKWebView.alloc().initWithFrame_(
            NSMakeRect(0, 0, 360, 400)
        )
        self.webview.setAutoresizingMask_(18)  # 自动调整大小

        # 设置透明背景
        self.webview.setValue_forKey_(False, "drawsBackground")

        # 加载 URL
        request = NSURLRequest.requestWithURL_(NSURL.URLWithString_(self.url))
        self.webview.loadRequest_(request)

        # 将 WebView 添加到毛玻璃视图
        effect_view.addSubview_(self.webview)

        # 设置为控制器的视图
        self.setView_(effect_view)


class AIGuardDelegate(NSObject):
    """应用委托"""

    def init(self):
        print("=== AIGuardDelegate.init() 开始 ===")
        self = objc.super(AIGuardDelegate, self).init()
        if self is None:
            print("❌ super().init() 返回 None")
            return None

        print("✅ super().init() 成功")

        # 读取服务地址
        try:
            print("正在读取服务配置...")
            host = _main_mod.SERVER_CFG.get("host", "127.0.0.1")
            port = _main_mod.SERVER_CFG.get("port", 8765)
            self.url = f"http://{host}:{port}"
            print(f"✅ 服务地址: {self.url}")
        except Exception as e:
            print(f"❌ 读取配置失败: {e}")
            import traceback
            traceback.print_exc()
            return None

        # 创建状态栏项
        print("=== 开始创建状态栏项 ===")
        statusBar = NSStatusBar.systemStatusBar()
        print(f"状态栏对象: {statusBar}")

        self.statusItem = statusBar.statusItemWithLength_(NSVariableStatusItemLength)
        print(f"状态栏项: {self.statusItem}")

        # 设置按钮属性
        button = self.statusItem.button()
        print(f"按钮对象: {button}")

        if button:
            button.setTitle_("AI Guard")  # 设置明显的标题
            # 确保按钮可见
            button.setEnabled_(True)
            print("✅ 按钮已设置标题和启用")
        else:
            print("❌ 警告: 无法获取状态栏按钮")

        # 确保状态栏项可见
        self.statusItem.setVisible_(True)
        print("✅ 状态栏项已设置为可见")

        # 打印状态栏项的详细信息
        print(f"状态栏项是否可见: {self.statusItem.isVisible()}")
        print(f"状态栏项长度: {self.statusItem.length()}")
        print(f"按钮标题: {self.statusItem.button().title()}")
        print(f"按钮是否启用: {self.statusItem.button().isEnabled()}")

        # 创建 Popover
        self.popover = NSPopover.alloc().init()
        self.viewController = PopoverViewController.alloc().init()
        self.popover.setContentViewController_(self.viewController)
        self.popover.setBehavior_(1)  # NSPopoverBehaviorTransient

        # 创建原生窗口管理器（用于显示监控面板）
        from aigard.window_manager import DashboardWindow
        self.dashboard_window = DashboardWindow.get_instance(self.url)

        # 绑定点击事件
        self.statusItem.button().setAction_("togglePopover:")
        self.statusItem.button().setTarget_(self)

        # 创建菜单（右键或长按显示）
        self.menu = NSMenu.alloc().init()
        self._build_menu()

        # 启动后台服务
        self._start_server()

        # 启动定时器（每 5 秒刷新状态）
        self.timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            5.0, self, "refreshStatus:", None, True
        )

        # 强制激活应用并显示菜单栏
        print("正在激活应用...")
        NSApp.activateIgnoringOtherApps_(True)
        print("✅ 应用已激活")

        return self

    def _build_menu(self):
        """构建菜单"""
        # 打开监控面板
        item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "打开监控面板", "openPanel:", ""
        )
        item.setTarget_(self)
        self.menu.addItem_(item)

        # Claude 使用统计
        item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Claude 使用统计", "openUsage:", ""
        )
        item.setTarget_(self)
        self.menu.addItem_(item)

        self.menu.addItem_(NSMenuItem.separatorItem())

        # 状态行
        self.statusMenuItem = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "状态: 启动中...", None, ""
        )
        self.menu.addItem_(self.statusMenuItem)

        self.menu.addItem_(NSMenuItem.separatorItem())

        # 一键终止安全进程
        item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "一键终止安全进程", "killSafe:", ""
        )
        item.setTarget_(self)
        self.menu.addItem_(item)

        # 自动终止开关
        self.autoKillMenuItem = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "自动终止: 关", "toggleAutoKill:", ""
        )
        self.autoKillMenuItem.setTarget_(self)
        self.menu.addItem_(self.autoKillMenuItem)

        self.menu.addItem_(NSMenuItem.separatorItem())

        # 检查更新
        item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "检查更新", "checkUpdate:", ""
        )
        item.setTarget_(self)
        self.menu.addItem_(item)

        # 偏好设置
        item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "偏好设置", "openConfig:", ""
        )
        item.setTarget_(self)
        self.menu.addItem_(item)

        self.menu.addItem_(NSMenuItem.separatorItem())

        # 退出
        item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "退出 AI Guard", "terminate:", ""
        )
        item.setTarget_(NSApp)
        self.menu.addItem_(item)

    def _start_server(self):
        """启动后台服务"""
        self.server_thread = threading.Thread(
            target=_main_mod.start_server, daemon=True
        )
        self.server_thread.start()

    def togglePopover_(self, sender):
        """切换 Popover 显示/隐藏"""
        if self.popover.isShown():
            self.popover.close()
        else:
            # 显示 Popover
            button = self.statusItem.button()
            self.popover.showRelativeToRect_ofView_preferredEdge_(
                button.bounds(),
                button,
                3  # NSRectEdgeMinY - 从下方弹出
            )

    def rightMouseDown_(self, event):
        """右键点击显示菜单"""
        self.statusItem.popUpStatusItemMenu_(self.menu)

    def openPanel_(self, sender):
        """打开监控面板（浏览器）"""
        webbrowser.open(self.url)

    def openUsage_(self, sender):
        """打开使用统计（原生窗口）"""
        self.dashboard_window.load_url(f"{self.url}/usage.html")
        self.dashboard_window.show()

    def killSafe_(self, sender):
        """一键终止安全进程"""
        from aigard.core import kill_process
        threads = _main_mod.threads
        with threads.lock:
            safe_procs = [p for p in threads.latest_processes if p.get("risk") == "safe"]

        if not safe_procs:
            return

        killed = 0
        for proc in safe_procs:
            r = kill_process(proc["pid"])
            if r.success:
                killed += 1

    def toggleAutoKill_(self, sender):
        """切换自动终止"""
        threads = _main_mod.threads
        with threads.lock:
            threads.autokill_enabled = not threads.autokill_enabled
            state = threads.autokill_enabled
        self.autoKillMenuItem.setTitle_(f"自动终止: {'开' if state else '关'}")

    def checkUpdate_(self, sender):
        """检查更新"""
        import requests
        try:
            resp = requests.get(f"{self.url}/api/update/check", timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('has_update') and data.get('html_url'):
                    webbrowser.open(data['html_url'])
        except:
            pass

    def openConfig_(self, sender):
        """打开配置文件"""
        import subprocess
        config_path = Path(__file__).parent / "config.toml"
        subprocess.run(["open", "-t", str(config_path)], check=False)

    def refreshStatus_(self, timer):
        """刷新状态"""
        latest = _main_mod.history.latest
        if not latest:
            self.statusItem.button().setTitle_("...")
            return

        mem = latest.get("mem_percent", 0)
        cpu = latest.get("cpu_percent", 0)
        swap = latest.get("swap_percent", 0)
        disk = latest.get("disk_percent", 0)
        level = latest.get("alert_level", "normal")

        # 菜单栏标题
        if level == "crit":
            self.statusItem.button().setTitle_(f"⚠︎{mem:.0f}%")
        elif level == "warn":
            self.statusItem.button().setTitle_(f"△{mem:.0f}%")
        else:
            self.statusItem.button().setTitle_(f"{mem:.0f}%")

        # 状态行
        usage = _main_mod.threads.get_today_usage()
        usage_str = ""
        if usage and usage.get('total_tokens', 0) > 0:
            tokens = usage['total_tokens']
            cost = usage.get('total_cost', 0)
            if tokens >= 1_000_000:
                token_str = f"{tokens / 1_000_000:.1f}M"
            elif tokens >= 1000:
                token_str = f"{tokens / 1000:.0f}K"
            else:
                token_str = str(tokens)
            usage_str = f" | Token {token_str} ${cost:.2f}"

        self.statusMenuItem.setTitle_(
            f"CPU {cpu:.0f}% / Mem {mem:.0f}% / Swap {swap:.0f}% / Disk {disk:.0f}%{usage_str}"
        )

        # 同步自动终止开关
        state = _main_mod.threads.autokill_enabled
        self.autoKillMenuItem.setTitle_(f"自动终止: {'开' if state else '关'}")


def main():
    print("=== main() 开始 ===")
    try:
        print("正在获取 NSApplication...")
        app = NSApplication.sharedApplication()
        print(f"✅ NSApplication: {app}")

        print("正在创建 AIGuardDelegate...")
        delegate = AIGuardDelegate.alloc().init()
        print(f"✅ AIGuardDelegate: {delegate}")

        if delegate is None:
            print("❌ 错误: delegate 为 None!")
            return

        print("正在设置 delegate...")
        app.setDelegate_(delegate)
        print("✅ delegate 已设置")

        print("正在启动事件循环...")
        app.run()
        print("事件循环已退出")
    except Exception as e:
        print(f"❌ main() 异常: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
