"""app_native.py - Native macOS menubar app (Pure PyObjC with Popover support)

Usage:
    python app_native.py          # Development mode
    open "dist/AI Guard.app"      # After packaging
"""

import os
import sys
import io

os.environ['PYTHONIOENCODING'] = 'utf-8'
log_file = open('/tmp/aigard_native.log', 'wb', buffering=0)
sys.stdout = io.TextIOWrapper(log_file, encoding='utf-8', line_buffering=True, write_through=True, errors='replace')
sys.stderr = sys.stdout

print("=== app_native started ===")

sys.path.insert(0, '/Users/rocalight/Desktop/All in one Data/01_PROJECTS/AI Guard')
os.environ["AIGARD_NO_BROWSER"] = "1"
import importlib
_main_mod = importlib.import_module('main')
print("main loaded")

import threading

from AppKit import NSApplication, NSStatusBar, NSVariableStatusItemLength, NSMenu, NSMenuItem, NSApp, NSPopover, NSImage, NSColor, NSBezierPath
from WebKit import WKWebView
from Foundation import NSMakeSize, NSTimer, NSMakeRect

from aigard.popover import PopoverViewController
from aigard.window_manager import DashboardWindow
print("All imports done")

import objc
from Foundation import NSObject


def create_status_icon(color_name="white"):
    """加载菜单栏图标"""
    from pathlib import Path

    # 获取图标路径（支持开发模式和打包模式）
    if getattr(sys, 'frozen', False):
        # 打包模式
        base_path = Path(sys._MEIPASS if hasattr(sys, '_MEIPASS') else os.path.dirname(sys.executable)).parent / 'Resources'
    else:
        # 开发模式
        base_path = Path(__file__).parent

    icon_path = str(base_path / 'assets' / 'menubar_icon.png')

    # 加载图标
    img = NSImage.alloc().initWithContentsOfFile_(icon_path)
    if img is None:
        print(f"警告：无法加载图标 {icon_path}，使用备用圆点")
        # 备用方案：创建圆点
        size = 18
        img = NSImage.alloc().initWithSize_((size, size))
        img.lockFocus()
        if color_name == "red":
            NSColor.redColor().setFill()
        elif color_name == "yellow":
            NSColor.yellowColor().setFill()
        else:
            NSColor.whiteColor().setFill()
        path = NSBezierPath.bezierPathWithOvalInRect_(NSMakeRect(2, 2, size-4, size-4))
        path.fill()
        img.unlockFocus()
    else:
        # 调整图标大小为菜单栏标准尺寸
        img.setSize_((18, 18))
        print(f"✅ 已加载图标：{icon_path}")

    img.setTemplate_(True)  # 使用模板模式，自动适配亮/暗色主题
    return img


class AIGuardDelegate(NSObject):
    # 菜单项翻译
    MENU_TEXTS = {
        'zh': {
            'about': '关于',
            'monitor': '监控面板',
            'usage': '使用统计',
            'kill_safe': '终止安全进程',
            'auto_kill_on': '自动终止: 开',
            'auto_kill_off': '自动终止: 关',
            'check_updates': '检查更新...',
            'preferences': '偏好设置...',
            'quit': '退出 AI Guard'
        },
        'en': {
            'about': 'About',
            'monitor': 'Monitor Panel',
            'usage': 'Usage Stats',
            'kill_safe': 'Kill Safe',
            'auto_kill_on': 'Auto Kill: On',
            'auto_kill_off': 'Auto Kill: Off',
            'check_updates': 'Check Updates...',
            'preferences': 'Preferences...',
            'quit': 'Quit AI Guard'
        }
    }

    def _load_language(self):
        """从 config.toml 读取语言配置"""
        try:
            # 使用 Python 3.11+ 标准库的 tomllib
            import tomllib
            from pathlib import Path

            # 优先读取用户配置目录的 config.toml（与后端 API 保持一致）
            user_config = Path.home() / '.aigard' / 'config.toml'

            # 如果用户配置不存在，使用应用内置配置
            if not user_config.exists():
                if getattr(sys, 'frozen', False):
                    # 打包模式
                    if hasattr(sys, '_MEIPASS'):
                        base_path = Path(sys._MEIPASS)
                    else:
                        base_path = Path(sys.executable).parent.parent / 'Resources'
                else:
                    # 开发模式
                    base_path = Path(__file__).parent
                config_path = base_path / 'config.toml'
            else:
                config_path = user_config

            if config_path.exists():
                with open(config_path, 'rb') as f:
                    config = tomllib.load(f)
                return config.get('ui', {}).get('language', 'en')
        except Exception as e:
            print(f"加载语言配置失败: {e}")
            import traceback
            traceback.print_exc()
        return 'en'

    def init(self):
        print("=== AIGuardDelegate.init() started ===")
        self = objc.super(AIGuardDelegate, self).init()
        if self is None:
            print("ERROR: super().init() returned None")
            return None

        print("SUCCESS: super().init() completed")

        host = _main_mod.SERVER_CFG.get("host", "127.0.0.1")
        port = _main_mod.SERVER_CFG.get("port", 8765)
        self.url = f"http://{host}:{port}"
        print(f"Service URL: {self.url}")

        # 读取语言配置
        self.current_lang = self._load_language()
        print(f"Language: {self.current_lang}")

        print("=== Creating status bar item ===")
        self.statusItem = NSStatusBar.systemStatusBar().statusItemWithLength_(
            NSVariableStatusItemLength
        )
        print(f"Status item: {self.statusItem}")
        self.statusItem.setVisible_(True)
        print(f"Status item visible: {self.statusItem.isVisible()}")

        # 创建默认图标
        self.icon_normal = create_status_icon("white")
        self.icon_warn = create_status_icon("yellow")
        self.icon_crit = create_status_icon("red")
        print("Icons created")

        print("=== AIGuardDelegate.init() completed ===")
        return self

    def applicationDidFinishLaunching_(self, notification):
        print("=== applicationDidFinishLaunching_ called ===")

        button = self.statusItem.button()
        print(f"Button: {button}")
        if button:
            button.setImage_(self.icon_normal)
            button.setEnabled_(True)
            print("Button icon set")

        # Full menu
        menu = NSMenu.alloc().init()
        self.aboutMenuItem = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("About", "showAbout:", "")
        self.aboutMenuItem.setTarget_(self)
        menu.addItem_(self.aboutMenuItem)
        menu.addItem_(NSMenuItem.separatorItem())
        self.monitorMenuItem = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Monitor Panel", "openPanel:", "")
        self.monitorMenuItem.setTarget_(self)
        menu.addItem_(self.monitorMenuItem)
        self.usageMenuItem = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Usage Stats", "openUsage:", "")
        self.usageMenuItem.setTarget_(self)
        menu.addItem_(self.usageMenuItem)
        menu.addItem_(NSMenuItem.separatorItem())
        self.statusMenuItem = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "CPU 0% · Mem 0% · Swap 0%", None, ""
        )
        menu.addItem_(self.statusMenuItem)
        menu.addItem_(NSMenuItem.separatorItem())
        self.killSafeMenuItem = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Kill Safe", "killSafe:", "")
        self.killSafeMenuItem.setTarget_(self)
        menu.addItem_(self.killSafeMenuItem)
        self.autoKillMenuItem = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Auto Kill: Off", "toggleAutoKill:", "")
        self.autoKillMenuItem.setTarget_(self)
        menu.addItem_(self.autoKillMenuItem)
        menu.addItem_(NSMenuItem.separatorItem())
        self.checkUpdatesMenuItem = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Check Updates...", "checkUpdate:", "")
        self.checkUpdatesMenuItem.setTarget_(self)
        menu.addItem_(self.checkUpdatesMenuItem)
        self.preferencesMenuItem = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Preferences...", "openConfig:", ",")
        self.preferencesMenuItem.setTarget_(self)
        menu.addItem_(self.preferencesMenuItem)
        menu.addItem_(NSMenuItem.separatorItem())
        self.quitMenuItem = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Quit AI Guard", "terminate:", "q")
        self.quitMenuItem.setTarget_(NSApp)
        menu.addItem_(self.quitMenuItem)
        self.statusItem.setMenu_(menu)
        print("Menu set")

        # 初始化菜单语言
        self.updateMenuLanguage()

        try:
            self.popover_controller = PopoverViewController.alloc().initWithThreadsManager_serverUrl_(
                _main_mod.threads, self.url
            )
            self.popover = NSPopover.alloc().init()
            self.popover.setContentViewController_(self.popover_controller)
            self.popover.setBehavior_(0)
            self.popover.setContentSize_(NSMakeSize(360, 550))
            print("Popover created")
        except Exception as e:
            print(f"Popover failed: {e}")
            import traceback
            traceback.print_exc()

        try:
            self.dashboard_window = DashboardWindow.get_instance(self.url)
            print("DashboardWindow created")
        except Exception as e:
            print(f"DashboardWindow failed: {e}")
            import traceback
            traceback.print_exc()

        self.server_thread = threading.Thread(target=_main_mod.start_server, daemon=True)
        self.server_thread.start()
        print("server started")

        self.timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            5.0, self, "refreshStatus:", None, True
        )
        print("Timer started")

        # 启动语言配置检查定时器（每5秒检查一次）
        self.lang_timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            5.0, self, "checkLanguageChange:", None, True
        )
        print("Language check timer started")

        print("=== applicationDidFinishLaunching_ completed ===")

    def updateMenuLanguage(self):
        """更新菜单项语言"""
        texts = self.MENU_TEXTS.get(self.current_lang, self.MENU_TEXTS['en'])
        self.aboutMenuItem.setTitle_(texts['about'])
        self.monitorMenuItem.setTitle_(texts['monitor'])
        self.usageMenuItem.setTitle_(texts['usage'])
        self.killSafeMenuItem.setTitle_(texts['kill_safe'])
        self.checkUpdatesMenuItem.setTitle_(texts['check_updates'])
        self.preferencesMenuItem.setTitle_(texts['preferences'])
        self.quitMenuItem.setTitle_(texts['quit'])
        # autoKillMenuItem 的标题在 refreshStatus_ 中动态更新

    def checkLanguageChange_(self, timer):
        """检查语言配置是否变化"""
        new_lang = self._load_language()
        if new_lang != self.current_lang:
            print(f"Language changed: {self.current_lang} -> {new_lang}")
            self.current_lang = new_lang
            self.updateMenuLanguage()

    def refreshStatus_(self, timer):
        latest = _main_mod.history.latest
        if not latest:
            return
        mem = latest.get("mem_percent", 0)
        cpu = latest.get("cpu_percent", 0)
        swap = latest.get("swap_percent", 0)
        level = latest.get("alert_level", "normal")

        # 根据告警等级切换图标颜色
        if level == "crit":
            self.statusItem.button().setImage_(self.icon_crit)
        elif level == "warn":
            self.statusItem.button().setImage_(self.icon_warn)
        else:
            self.statusItem.button().setImage_(self.icon_normal)

        self.statusMenuItem.setTitle_(f"CPU {cpu:.0f}% · Mem {mem:.0f}% · Swap {swap:.0f}%")
        state = _main_mod.threads.autokill_enabled
        # 根据当前语言更新自动终止菜单项
        texts = self.MENU_TEXTS.get(self.current_lang, self.MENU_TEXTS['en'])
        self.autoKillMenuItem.setTitle_(texts['auto_kill_on'] if state else texts['auto_kill_off'])

    def showAbout_(self, sender):
        from AppKit import NSAlert, NSAlertStyleInformational
        alert = NSAlert.alloc().init()
        alert.setMessageText_("About AI Guard")
        alert.setInformativeText_(f"Version: {_main_mod.VERSION}\n\nMac AI Development Resource Guardian\nMonitor + Alert + Safe Intervention + Usage Stats\n\n© 2026 AI Guard\nhttps://github.com/Xaiver03/ai-guard")
        alert.setAlertStyle_(NSAlertStyleInformational)
        alert.addButtonWithTitle_("OK")
        alert.runModal()

    def openPanel_(self, sender):
        import webbrowser
        webbrowser.open(self.url)

    def openUsage_(self, sender):
        self.dashboard_window.load_url(f"{self.url}/usage.html")
        self.dashboard_window.show()

    def openTools_(self, sender):
        self.dashboard_window.load_url(f"{self.url}/tools.html")
        self.dashboard_window.show()

    def openPractices_(self, sender):
        self.dashboard_window.load_url(f"{self.url}/practices.html")
        self.dashboard_window.show()

    def killSafe_(self, sender):
        from aigard.core import kill_process
        threads = _main_mod.threads
        my_pid = os.getpid()
        my_ppid = os.getppid()
        with threads.lock:
            safe_procs = [p for p in threads.latest_processes if p.get("risk") == "safe"]
        for proc in safe_procs:
            pid = proc["pid"]
            # Self-protection: never kill AI Guard itself or its parent
            if pid == my_pid or pid == my_ppid:
                continue
            kill_process(pid)

    def toggleAutoKill_(self, sender):
        threads = _main_mod.threads
        with threads.lock:
            threads.autokill_enabled = not threads.autokill_enabled
            state = threads.autokill_enabled
        self.autoKillMenuItem.setTitle_(f"Auto Kill: {'On' if state else 'Off'}")

    def checkUpdate_(self, sender):
        import requests
        try:
            resp = requests.get(f"{self.url}/api/update/check", timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('has_update') and data.get('html_url'):
                    import webbrowser
                    webbrowser.open(data['html_url'])
        except Exception:
            pass

    def openConfig_(self, sender):
        """打开监控面板并显示设置侧边栏"""
        self.dashboard_window.load_url(self.url)
        self.dashboard_window.show()
        # 等待页面加载后触发设置侧边栏
        import time
        time.sleep(0.5)
        # 通过 JavaScript 打开设置
        js_code = "openSettings()"
        self.dashboard_window.webview.evaluateJavaScript_completionHandler_(js_code, None)


def main():
    app = NSApplication.sharedApplication()
    # macOS Tahoe 兼容：使用 NSApplicationActivationPolicyRegular (0)
    # setActivationPolicy_(2) 在 Tahoe 上会导致状态栏项不显示
    app.setActivationPolicy_(0)
    delegate = AIGuardDelegate.alloc().init()
    if delegate is None:
        return
    app.setDelegate_(delegate)
    app.run()


if __name__ == "__main__":
    main()