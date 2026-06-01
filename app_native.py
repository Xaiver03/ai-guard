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
    """创建菜单栏图标（圆点）"""
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
    img.setTemplate_(True)  # 使用模板模式，自动适配亮/暗色主题
    return img


class AIGuardDelegate(NSObject):

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
        item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("About", "showAbout:", "")
        item.setTarget_(self)
        menu.addItem_(item)
        menu.addItem_(NSMenuItem.separatorItem())
        item2 = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Monitor Panel", "openPanel:", "")
        item2.setTarget_(self)
        menu.addItem_(item2)
        item3 = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Usage Stats", "openUsage:", "")
        item3.setTarget_(self)
        menu.addItem_(item3)
        menu.addItem_(NSMenuItem.separatorItem())
        self.statusMenuItem = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "CPU 0% · Mem 0% · Swap 0%", None, ""
        )
        menu.addItem_(self.statusMenuItem)
        menu.addItem_(NSMenuItem.separatorItem())
        item4 = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Kill Safe", "killSafe:", "")
        item4.setTarget_(self)
        menu.addItem_(item4)
        self.autoKillMenuItem = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Auto Kill: Off", "toggleAutoKill:", "")
        self.autoKillMenuItem.setTarget_(self)
        menu.addItem_(self.autoKillMenuItem)
        menu.addItem_(NSMenuItem.separatorItem())
        item5 = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Check Updates...", "checkUpdate:", "")
        item5.setTarget_(self)
        menu.addItem_(item5)
        item6 = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Preferences...", "openConfig:", ",")
        item6.setTarget_(self)
        menu.addItem_(item6)
        menu.addItem_(NSMenuItem.separatorItem())
        item7 = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Quit AI Guard", "terminate:", "q")
        item7.setTarget_(NSApp)
        menu.addItem_(item7)
        self.statusItem.setMenu_(menu)
        print("Menu set")

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

        print("=== applicationDidFinishLaunching_ completed ===")

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
        self.autoKillMenuItem.setTitle_(f"Auto Kill: {'On' if state else 'Off'}")

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
        import subprocess
        from pathlib import Path
        config_path = Path(__file__).parent / "config.toml"
        subprocess.run(["open", "-t", str(config_path)], check=False)


def main():
    app = NSApplication.sharedApplication()
    # NSApplicationActivationPolicyAccessory = 2 (menu bar only, no dock icon)
    app.setActivationPolicy_(2)
    delegate = AIGuardDelegate.alloc().init()
    if delegate is None:
        return
    app.setDelegate_(delegate)
    app.run()


if __name__ == "__main__":
    main()