"""app_native.py - Native macOS menubar app (Pure PyObjC with Popover support)

Usage:
    python app_native.py          # Development mode
    open "dist/AI Guard.app"      # After packaging
"""

import os
import sys
import io

# Set UTF-8 encoding BEFORE any other imports to prevent UnicodeEncodeError
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['LC_ALL'] = 'en_US.UTF-8'
os.environ['LANG'] = 'en_US.UTF-8'

# Redirect stdout/stderr to log file with UTF-8 encoding IMMEDIATELY
log_file = open('/tmp/aigard_native.log', 'wb', buffering=0)
sys.stdout = io.TextIOWrapper(log_file, encoding='utf-8', line_buffering=True, write_through=True, errors='replace')
sys.stderr = sys.stdout

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

# Prevent main.py's on_startup from auto-opening browser
os.environ["AIGARD_NO_BROWSER"] = "1"

# Ensure we can import main.py from the same directory
# After packaging, main.py is in the Resources directory
if getattr(sys, 'frozen', False):
    # Path after packaging: sys.executable is .../MacOS/AI Guard
    # We need to go up to Contents, then into Resources
    bundle_dir = Path(sys.executable).parent.parent  # MacOS -> Contents
    resources_dir = bundle_dir / 'Resources'
    if resources_dir.exists():
        sys.path.insert(0, str(resources_dir))
        print(f"[DEBUG] Added to sys.path: {resources_dir}", flush=True)
    else:
        print(f"[ERROR] Resources directory not found: {resources_dir}", flush=True)
        sys.path.insert(0, str(bundle_dir))
    print(f"[DEBUG] sys.path: {sys.path}", flush=True)
else:
    # Development mode
    sys.path.insert(0, str(Path(__file__).parent))

import importlib
_main_mod = importlib.import_module('main')


class AIGuardDelegate(NSObject):
    """Application delegate"""

    def init(self):
        print("=== AIGuardDelegate.init() started ===")
        self = objc.super(AIGuardDelegate, self).init()
        if self is None:
            print("ERROR: super().init() returned None")
            return None

        print("SUCCESS: super().init() completed")

        # Read service address
        host = _main_mod.SERVER_CFG.get("host", "127.0.0.1")
        port = _main_mod.SERVER_CFG.get("port", 8765)
        self.url = f"http://{host}:{port}"
        print(f"Service URL: {self.url}")

        return self

    def applicationDidFinishLaunching_(self, notification):
        """Callback after application finishes launching"""
        print("=== applicationDidFinishLaunching_ called ===")

        # Create status bar item
        print("=== Creating status bar item ===")
        self.statusItem = NSStatusBar.systemStatusBar().statusItemWithLength_(
            NSVariableStatusItemLength
        )
        print(f"Status item: {self.statusItem}")

        # Set button properties
        button = self.statusItem.button()
        print(f"Button: {button}")
        if button:
            # Set text title as fallback
            button.setTitle_("AG")

            # Load icon
            try:
                from AppKit import NSImage
                import os
                icon_path = os.path.join(
                    os.path.dirname(__file__),
                    "assets/menubar_icon.png"
                )
                print(f"Icon path: {icon_path}")
                print(f"Icon file exists: {os.path.exists(icon_path)}")

                if os.path.exists(icon_path):
                    icon = NSImage.alloc().initWithContentsOfFile_(icon_path)
                    if icon:
                        # Set icon size (standard menubar size)
                        from Foundation import NSMakeSize
                        icon.setSize_(NSMakeSize(18, 18))
                        # Set as template icon (auto-adapt light/dark mode)
                        icon.setTemplate_(True)
                        button.setImage_(icon)
                        # Clear text, show icon only
                        button.setTitle_("")
                        print(f"✅ Icon set: {icon_path}, size: {icon.size()}, template: {icon.isTemplate()}")
                    else:
                        print("❌ Icon object creation failed, keeping text AG")
                else:
                    print(f"❌ Icon file not found: {icon_path}, keeping text AG")
            except Exception as e:
                print(f"❌ Icon loading error: {e}, keeping text AG")
                import traceback
                traceback.print_exc()

            button.setEnabled_(True)
            print("Button enabled")

        # Ensure status item is visible
        self.statusItem.setVisible_(True)
        self.statusItem.setLength_(NSVariableStatusItemLength)
        print(f"Status item visible: {self.statusItem.isVisible()}")
        print(f"Status item length: {self.statusItem.length()}")

        # Force refresh status bar
        button = self.statusItem.button()
        if button:
            button.setNeedsDisplay_(True)
            print("Button display refreshed")

        # Create Popover (using native AppKit controls)
        print("=== Creating Popover ===")
        try:
            from aigard.popover import PopoverViewController
            print("PopoverViewController imported")

            # Create view controller
            self.popover_controller = PopoverViewController.alloc().initWithThreadsManager_serverUrl_(
                _main_mod.threads,
                self.url
            )
            print(f"PopoverViewController created")

            # Create Popover
            from AppKit import NSPopover
            self.popover = NSPopover.alloc().init()
            self.popover.setContentViewController_(self.popover_controller)
            self.popover.setBehavior_(0)  # NSPopoverBehaviorApplicationDefined
            from Foundation import NSMakeSize
            self.popover.setContentSize_(NSMakeSize(360, 550))  # Increased height for charts
            print(f"Popover created")
        except Exception as e:
            print(f"Failed to create Popover: {e}")
            import traceback
            traceback.print_exc()

        # Create native window manager (for dashboard)
        print("=== Creating DashboardWindow ===")
        try:
            from aigard.window_manager import DashboardWindow
            self.dashboard_window = DashboardWindow.get_instance(self.url)
            print(f"DashboardWindow created: {self.dashboard_window}")
        except Exception as e:
            print(f"Failed to create DashboardWindow: {e}")
            import traceback
            traceback.print_exc()

        # Bind click event - left click shows Popover
        self.statusItem.button().setAction_("togglePopover:")
        self.statusItem.button().setTarget_(self)

        # Create menu
        self.menu = NSMenu.alloc().init()
        self._build_menu()

        # Start background service
        self._start_server()

        # Start timer (refresh status every 5 seconds)
        self.timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            5.0, self, "refreshStatus:", None, True
        )

        print("=== applicationDidFinishLaunching_ completed ===")

    def _build_menu(self):
        """Build menu"""
        # About
        item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "关于 AI Guard", "showAbout:", ""
        )
        item.setTarget_(self)
        self.menu.addItem_(item)

        self.menu.addItem_(NSMenuItem.separatorItem())

        # Monitoring Panel
        item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "监控面板", "openPanel:", ""
        )
        item.setTarget_(self)
        self.menu.addItem_(item)

        # Usage Statistics
        item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "使用统计", "openUsage:", ""
        )
        item.setTarget_(self)
        self.menu.addItem_(item)

        # AI Tools Navigation
        item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "AI 工具导航", "openTools:", ""
        )
        item.setTarget_(self)
        self.menu.addItem_(item)

        # Best Practices
        item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "最佳实践", "openPractices:", ""
        )
        item.setTarget_(self)
        self.menu.addItem_(item)

        self.menu.addItem_(NSMenuItem.separatorItem())

        # Status line (simplified display)
        self.statusMenuItem = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "CPU 0% · 内存 0% · Swap 0%", None, ""
        )
        self.menu.addItem_(self.statusMenuItem)

        self.menu.addItem_(NSMenuItem.separatorItem())

        # One-Click Terminate
        item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "一键终止", "killSafe:", ""
        )
        item.setTarget_(self)
        self.menu.addItem_(item)

        # Auto Terminate
        self.autoKillMenuItem = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "自动终止: 关", "toggleAutoKill:", ""
        )
        self.autoKillMenuItem.setTarget_(self)
        self.menu.addItem_(self.autoKillMenuItem)

        self.menu.addItem_(NSMenuItem.separatorItem())

        # Check for Updates
        item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "检查更新...", "checkUpdate:", ""
        )
        item.setTarget_(self)
        self.menu.addItem_(item)

        # Preferences (add shortcut ⌘,)
        item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "偏好设置...", "openConfig:", ","
        )
        item.setTarget_(self)
        self.menu.addItem_(item)

        self.menu.addItem_(NSMenuItem.separatorItem())

        # Quit (add shortcut ⌘Q)
        item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "退出 AI Guard", "terminate:", "q"
        )
        item.setTarget_(NSApp)
        self.menu.addItem_(item)

    def _start_server(self):
        """Start background service"""
        self.server_thread = threading.Thread(
            target=_main_mod.start_server, daemon=True
        )
        self.server_thread.start()

    def togglePopover_(self, sender):
        """Toggle Popover show/hide"""
        print(f"=== togglePopover_ called, sender: {sender} ===")
        try:
            if self.popover.isShown():
                print("Close Popover")
                self.popover.close()
            else:
                print("Show Popover")
                button = self.statusItem.button()
                print(f"Button: {button}, bounds: {button.bounds()}")
                self.popover.showRelativeToRect_ofView_preferredEdge_(
                    button.bounds(),
                    button,
                    3  # NSRectEdgeMinY - 从下方弹出
                )
                # Update data
                self.popover_controller.update_metrics()
                self.popover_controller.update_usage()
                self.popover_controller.update_autokill_button()
                print("✅ Popover displayed successfully")
        except Exception as e:
            print(f"❌ togglePopover_ failed: {e}")
            import traceback
            traceback.print_exc()

    def showMenu_(self, sender):
        """Show menu"""
        self.statusItem.popUpStatusItemMenu_(self.menu)

    def showAbout_(self, sender):
        """Show about dialog"""
        from AppKit import NSAlert, NSAlertStyleInformational
        alert = NSAlert.alloc().init()
        alert.setMessageText_("About AI Guard")
        alert.setInformativeText_(
            f"Version: {_main_mod.VERSION}\n\n"
            "Mac AI Development Resource Guardian\n"
            "Monitor + Alert + Safe Intervention + Usage Stats\n\n"
            "© 2026 AI Guard\n"
            "https://github.com/Xaiver03/ai-guard"
        )
        alert.setAlertStyle_(NSAlertStyleInformational)
        alert.addButtonWithTitle_("OK")
        alert.runModal()

    def openPanel_(self, sender):
        """Open monitoring panel (browser)"""
        webbrowser.open(self.url)

    def openUsage_(self, sender):
        """Open usage statistics (native window)"""
        self.dashboard_window.load_url(f"{self.url}/usage.html")
        self.dashboard_window.show()

    def openTools_(self, sender):
        """Open AI tools navigation (native window)"""
        self.dashboard_window.load_url(f"{self.url}/tools.html")
        self.dashboard_window.show()

    def openPractices_(self, sender):
        """Open best practices (native window)"""
        self.dashboard_window.load_url(f"{self.url}/practices.html")
        self.dashboard_window.show()

    def killSafe_(self, sender):
        """One-click terminate safe processes"""
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
        """Toggle auto terminate"""
        threads = _main_mod.threads
        with threads.lock:
            threads.autokill_enabled = not threads.autokill_enabled
            state = threads.autokill_enabled
        status_text = "on" if state else "off"
        self.autoKillMenuItem.setTitle_(f"Auto Kill: {status_text}")

    def checkUpdate_(self, sender):
        """Check for updates"""
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
        """Open config file"""
        import subprocess
        config_path = Path(__file__).parent / "config.toml"
        subprocess.run(["open", "-t", str(config_path)], check=False)

    def refreshStatus_(self, timer):
        """Refresh status"""
        latest = _main_mod.history.latest
        if not latest:
            # Keep icon, don't set title
            return

        mem = latest.get("mem_percent", 0)
        cpu = latest.get("cpu_percent", 0)
        swap = latest.get("swap_percent", 0)
        disk = latest.get("disk_percent", 0)
        level = latest.get("alert_level", "normal")

        # Don't modify menubar button display (keep icon)
        # Only update status info in menu items

        # Status line (simplified display)
        self.statusMenuItem.setTitle_(
            f"CPU {cpu:.0f}% · Mem {mem:.0f}% · Swap {swap:.0f}%"
        )

        # Sync auto-kill switch
        state = _main_mod.threads.autokill_enabled
        self.autoKillMenuItem.setTitle_(f"Auto Kill: {'On' if state else 'Off'}")


def main():
    from AppKit import NSApplicationActivationPolicyAccessory
    app = NSApplication.sharedApplication()

    # Set to Accessory mode (only show menu bar, no Dock icon)
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)

    delegate = AIGuardDelegate.alloc().init()
    if delegate is None:
        return
    app.setDelegate_(delegate)
    app.run()


if __name__ == "__main__":
    main()
