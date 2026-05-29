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


class AIGuardDelegate(NSObject):
    """应用委托"""

    def init(self):
        import sys
        sys.stdout = open('/tmp/aigard_native.log', 'w', encoding='utf-8', buffering=1)
        sys.stderr = sys.stdout

        print("=== AIGuardDelegate.init() 开始 ===")
        self = objc.super(AIGuardDelegate, self).init()
        if self is None:
            print("❌ super().init() 返回 None")
            return None

        print("✅ super().init() 成功")

        # 读取服务地址
        host = _main_mod.SERVER_CFG.get("host", "127.0.0.1")
        port = _main_mod.SERVER_CFG.get("port", 8765)
        self.url = f"http://{host}:{port}"
        print(f"✅ 服务地址: {self.url}")

        return self

    def applicationDidFinishLaunching_(self, notification):
        """应用启动完成后的回调"""
        print("=== applicationDidFinishLaunching_ 被调用 ===")

        # 创建状态栏项
        print("=== 创建状态栏项 ===")
        self.statusItem = NSStatusBar.systemStatusBar().statusItemWithLength_(
            NSVariableStatusItemLength
        )
        print(f"状态栏项: {self.statusItem}")

        # 设置按钮属性
        button = self.statusItem.button()
        print(f"按钮: {button}")
        if button:
            # 先设置一个文字标题作为后备
            button.setTitle_("AG")

            # 加载图标
            try:
                from AppKit import NSImage
                import os
                icon_path = os.path.join(
                    os.path.dirname(__file__),
                    "assets/menubar_icon.png"
                )
                print(f"图标路径: {icon_path}")
                print(f"图标文件存在: {os.path.exists(icon_path)}")

                if os.path.exists(icon_path):
                    icon = NSImage.alloc().initWithContentsOfFile_(icon_path)
                    if icon:
                        # 设置图标尺寸（菜单栏标准尺寸）
                        from Foundation import NSMakeSize
                        icon.setSize_(NSMakeSize(18, 18))
                        # 设置为模板图标（自动适配亮暗模式）
                        icon.setTemplate_(True)
                        button.setImage_(icon)
                        # 清除文字，只显示图标
                        button.setTitle_("")
                        print(f"✅ 图标已设置: {icon_path}, size: {icon.size()}, template: {icon.isTemplate()}")
                    else:
                        print("❌ 图标对象创建失败，保留文字 AG")
                else:
                    print(f"❌ 图标文件不存在: {icon_path}，保留文字 AG")
            except Exception as e:
                print(f"❌ 图标加载异常: {e}，保留文字 AG")
                import traceback
                traceback.print_exc()

            button.setEnabled_(True)
            print("✅ 按钮已设置")

        # 确保状态栏项可见
        self.statusItem.setVisible_(True)
        self.statusItem.setLength_(NSVariableStatusItemLength)
        print(f"✅ 状态栏项可见性: {self.statusItem.isVisible()}")
        print(f"✅ 状态栏项长度: {self.statusItem.length()}")

        # 强制刷新状态栏
        button = self.statusItem.button()
        if button:
            button.setNeedsDisplay_(True)
            print("✅ 强制刷新按钮显示")

        # 创建 Popover (使用原生 AppKit 控件)
        print("=== 创建 Popover ===")
        try:
            from aigard.popover import PopoverViewController
            print("✅ PopoverViewController 导入成功")

            # 创建视图控制器
            self.popover_controller = PopoverViewController.alloc().initWithThreadsManager_serverUrl_(
                _main_mod.threads,
                self.url
            )
            print(f"✅ PopoverViewController 创建成功")

            # 创建 Popover
            from AppKit import NSPopover
            self.popover = NSPopover.alloc().init()
            self.popover.setContentViewController_(self.popover_controller)
            self.popover.setBehavior_(0)  # NSPopoverBehaviorApplicationDefined
            from Foundation import NSMakeSize
            self.popover.setContentSize_(NSMakeSize(360, 550))  # 增加高度以容纳折线图
            print(f"✅ Popover 创建成功")
        except Exception as e:
            print(f"❌ Popover 创建失败: {e}")
            import traceback
            traceback.print_exc()

        # 创建原生窗口管理器（用于显示监控面板）
        print("=== 创建 DashboardWindow ===")
        try:
            from aigard.window_manager import DashboardWindow
            self.dashboard_window = DashboardWindow.get_instance(self.url)
            print(f"✅ DashboardWindow 创建成功: {self.dashboard_window}")
        except Exception as e:
            print(f"❌ DashboardWindow 创建失败: {e}")
            import traceback
            traceback.print_exc()

        # 绑定点击事件 - 左键显示 Popover
        self.statusItem.button().setAction_("togglePopover:")
        self.statusItem.button().setTarget_(self)

        # 创建菜单
        self.menu = NSMenu.alloc().init()
        self._build_menu()

        # 启动后台服务
        self._start_server()

        # 启动定时器（每 5 秒刷新状态）
        self.timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            5.0, self, "refreshStatus:", None, True
        )

        print("=== applicationDidFinishLaunching_ 完成 ===")

    def _build_menu(self):
        """构建菜单"""
        # 关于
        item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "关于 AI Guard", "showAbout:", ""
        )
        item.setTarget_(self)
        self.menu.addItem_(item)

        self.menu.addItem_(NSMenuItem.separatorItem())

        # 监控面板
        item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "监控面板", "openPanel:", ""
        )
        item.setTarget_(self)
        self.menu.addItem_(item)

        # 使用统计
        item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "使用统计", "openUsage:", ""
        )
        item.setTarget_(self)
        self.menu.addItem_(item)

        self.menu.addItem_(NSMenuItem.separatorItem())

        # 状态行 (简化显示)
        self.statusMenuItem = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "CPU 0% · 内存 0% · Swap 0%", None, ""
        )
        self.menu.addItem_(self.statusMenuItem)

        self.menu.addItem_(NSMenuItem.separatorItem())

        # 一键终止
        item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "一键终止", "killSafe:", ""
        )
        item.setTarget_(self)
        self.menu.addItem_(item)

        # 自动终止
        self.autoKillMenuItem = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "自动终止: 关", "toggleAutoKill:", ""
        )
        self.autoKillMenuItem.setTarget_(self)
        self.menu.addItem_(self.autoKillMenuItem)

        self.menu.addItem_(NSMenuItem.separatorItem())

        # 检查更新
        item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "检查更新...", "checkUpdate:", ""
        )
        item.setTarget_(self)
        self.menu.addItem_(item)

        # 偏好设置 (添加快捷键 ⌘,)
        item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "偏好设置...", "openConfig:", ","
        )
        item.setTarget_(self)
        self.menu.addItem_(item)

        self.menu.addItem_(NSMenuItem.separatorItem())

        # 退出 (添加快捷键 ⌘Q)
        item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "退出 AI Guard", "terminate:", "q"
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
        print(f"=== togglePopover_ 被调用,sender: {sender} ===")
        try:
            if self.popover.isShown():
                print("关闭 Popover")
                self.popover.close()
            else:
                print("显示 Popover")
                button = self.statusItem.button()
                print(f"按钮: {button}, bounds: {button.bounds()}")
                self.popover.showRelativeToRect_ofView_preferredEdge_(
                    button.bounds(),
                    button,
                    3  # NSRectEdgeMinY - 从下方弹出
                )
                # 更新数据
                self.popover_controller.update_metrics()
                self.popover_controller.update_usage()
                self.popover_controller.update_autokill_button()
                print("✅ Popover 显示完成")
        except Exception as e:
            print(f"❌ togglePopover_ 失败: {e}")
            import traceback
            traceback.print_exc()

    def showMenu_(self, sender):
        """显示菜单"""
        self.statusItem.popUpStatusItemMenu_(self.menu)

    def showAbout_(self, sender):
        """显示关于对话框"""
        from AppKit import NSAlert, NSAlertStyleInformational
        alert = NSAlert.alloc().init()
        alert.setMessageText_("关于 AI Guard")
        alert.setInformativeText_(
            f"版本: {_main_mod.VERSION}\n\n"
            "Mac AI 开发资源守护工具\n"
            "监控 + 告警 + 安全干预 + 使用统计\n\n"
            "© 2026 AI Guard\n"
            "https://github.com/Xaiver03/ai-guard"
        )
        alert.setAlertStyle_(NSAlertStyleInformational)
        alert.addButtonWithTitle_("确定")
        alert.runModal()

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
            # 不设置 title，保留图标
            return

        mem = latest.get("mem_percent", 0)
        cpu = latest.get("cpu_percent", 0)
        swap = latest.get("swap_percent", 0)
        disk = latest.get("disk_percent", 0)
        level = latest.get("alert_level", "normal")

        # 不修改菜单栏按钮的显示（保留图标）
        # 只更新菜单项中的状态信息

        # 状态行 (简化显示)
        self.statusMenuItem.setTitle_(
            f"CPU {cpu:.0f}% · 内存 {mem:.0f}% · Swap {swap:.0f}%"
        )

        # 同步自动终止开关
        state = _main_mod.threads.autokill_enabled
        self.autoKillMenuItem.setTitle_(f"自动终止: {'开' if state else '关'}")


def main():
    from AppKit import NSApplicationActivationPolicyAccessory
    app = NSApplication.sharedApplication()

    # 设置为 Accessory 模式（只显示菜单栏，不显示 Dock 图标）
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)

    delegate = AIGuardDelegate.alloc().init()
    if delegate is None:
        return
    app.setDelegate_(delegate)
    app.run()


if __name__ == "__main__":
    main()
