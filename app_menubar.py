"""app_menubar.py — macOS 菜单栏托盘入口（rumps + SF Symbols + NSPopover）

运行方式：
    python app_menubar.py          # 开发模式
    open "dist/AI Guard.app"       # 打包后

菜单栏图标：SF Symbol 模板图片（自动适配深色/浅色模式）
    正常：shield.fill
    警告：exclamationmark.triangle.fill
    危险：xmark.shield.fill

点击行为：显示 NSPopover 弹窗（原生 AppKit 控件）
"""

import os
import sys
import tempfile
import threading
import webbrowser
from pathlib import Path
from datetime import datetime, timedelta

import rumps
from AppKit import NSImage, NSPopover
from Foundation import NSObject

# 禁止 main.py 的 on_startup 自动打开浏览器（菜单栏模式下由用户手动点击）
os.environ["AIGARD_NO_BROWSER"] = "1"

# 确保能 import 到同级的 main.py
sys.path.insert(0, str(Path(__file__).parent))

# py2app 打包后，aigard 包在 Contents/Resources/lib/python3.9/ 下
# 需要确保能正确导入
import main as _main_mod


# ── SF Symbol → PNG 模板图片缓存 ─────────────────────────────

_ICON_CACHE_DIR = Path(tempfile.mkdtemp(prefix="aigard_icons_"))

def _sf_symbol_to_png(name: str, size: float = 18.0) -> str:
    """将 SF Symbol 导出为 PNG 文件路径（模板图片，黑色填充）
    rumps 的 icon setter 只接受文件路径，不接受 NSImage。
    """
    cache_path = _ICON_CACHE_DIR / f"{name}_{int(size)}.png"
    if cache_path.exists():
        return str(cache_path)

    img = NSImage.imageWithSystemSymbolName_accessibilityDescription_(name, None)
    if img is None:
        return _get_fallback_icon()

    img = img.copy()
    img.setSize_((size, size))
    img.setTemplate_(True)

    # 导出为 PNG
    from AppKit import NSBitmapImageRep, NSPNGFileType
    try:
        img.lockFocus()
        rep = NSBitmapImageRep.alloc().initWithFocusedViewRect_(
            ((0, 0), (size, size))
        )
        img.unlockFocus()
        png_data = rep.representationUsingType_properties_(NSPNGFileType, None)
        png_data.writeToFile_atomically_(str(cache_path), True)
        return str(cache_path)
    except Exception as e:
        print(f"[WARN] SF Symbol 转换失败: {e}，使用 fallback 图标")
        return _get_fallback_icon()


def _get_fallback_icon() -> str:
    """返回 fallback 图标路径（assets/menubar_icon.png）"""
    # 开发模式：从项目根目录读取
    dev_icon = Path(__file__).parent / "assets" / "menubar_icon.png"
    if dev_icon.exists():
        return str(dev_icon)

    # 打包模式（py2app）：从 __file__ 所在目录的 assets/ 读取
    # py2app 把 app_menubar.py 放在 Contents/Resources/ 下
    bundle_icon = Path(__file__).parent / "assets" / "menubar_icon.png"
    if bundle_icon.exists():
        return str(bundle_icon)

    # 尝试 icon.png 作为最后 fallback
    for name in ("menubar_icon.png", "icon.png"):
        fallback = Path(__file__).parent / "assets" / name
        if fallback.exists():
            return str(fallback)

    print("[ERROR] 找不到任何可用的图标文件")
    return None


# 三种状态图标
_SYMBOLS = {
    "normal": "shield.fill",
    "warn":   "exclamationmark.triangle.fill",
    "crit":   "xmark.shield.fill",
}


class _PopoverClickHandler(NSObject):
    """处理菜单栏按钮点击的 ObjC 类（NSObject 子类，用于 setTarget_/setAction_）"""

    popover = None
    nsstatusitem = None
    popover_controller = None

    def togglePopover_(self, sender):
        """点击菜单栏图标时触发"""
        if self.popover.isShown():
            self.popover.close()
        else:
            button = self.nsstatusitem.button()
            self.popover.showRelativeToRect_ofView_preferredEdge_(
                button.bounds(), button, 3  # NSMinYEdge (向下显示)
            )
            # 立即更新一次数据
            if self.popover_controller:
                self.popover_controller.update_metrics()
                self.popover_controller.update_usage()
                self.popover_controller.update_autokill_button()


class AIGuardApp(rumps.App):
    def __init__(self):
        # 使用纯黑色图标 + template 模式（macOS 菜单栏规范）
        icon_path = Path(__file__).parent / "assets" / "menubar_icon.png"

        super().__init__(
            name="AI Guard",
            title=None,
            icon=str(icon_path) if icon_path.exists() else None,
            template=True,
            quit_button=None,
        )

        # 读取服务地址
        host = _main_mod.SERVER_CFG.get("host", "127.0.0.1")
        port = _main_mod.SERVER_CFG.get("port", 8765)
        self._url = f"http://{host}:{port}"
        self._last_level = "normal"

        # 预生成三种状态图标缓存
        for name in _SYMBOLS.values():
            _sf_symbol_to_png(name)

        # 读取 usage 自动刷新间隔（秒），默认 1800 秒（30 分钟）
        usage_cfg = _main_mod.CFG.get("usage", {})
        self._usage_refresh_interval = usage_cfg.get("auto_refresh_interval", 1800)

        # 使用 Timer 替代轮询检查
        if self._usage_refresh_interval > 0:
            self._schedule_usage_refresh()

        # Popover 相关
        self._popover = None
        self._popover_controller = None

        # 空菜单（rumps 要求有 menu，但我们用 Popover 替代）
        self.menu = []

        # 在后台线程启动 FastAPI
        self._server_thread = threading.Thread(
            target=_main_mod.start_server, daemon=True
        )
        self._server_thread.start()

        # 每 15 秒刷新菜单栏状态
        self._timer = rumps.Timer(self._refresh_status, 15)
        self._timer.start()

        # 注册 before_start 回调，在 rumps 初始化 StatusBar 后替换为 Popover
        @rumps.events.before_start
        def _setup_popover():
            self._init_popover()

    # ── Popover 初始化 ──────────────────────────────────────

    def _init_popover(self):
        """在 rumps 初始化 StatusBar 后，替换默认菜单为 Popover"""
        from aigard.popover.controller import PopoverViewController

        # 创建 Popover
        self._popover = NSPopover.alloc().init()
        self._popover.setContentSize_((300, 520))  # 匹配 view_builder 中的容器高度
        self._popover.setBehavior_(1)  # NSPopoverBehaviorTransient (点击外部自动关闭)

        # 创建 PopoverViewController（使用 ObjC 风格初始化）
        self._popover_controller = PopoverViewController.alloc().initWithThreadsManager_serverUrl_(
            _main_mod.threads, self._url
        )
        self._popover.setContentViewController_(self._popover_controller)

        # 获取 NSStatusItem 并替换菜单为自定义点击行为
        nsstatusitem = self._nsapp.nsstatusitem
        button = nsstatusitem.button()

        nsstatusitem.setMenu_(None)  # 移除 rumps 的默认菜单

        # 创建 ObjC handler 对象来处理点击
        self._click_handler = _PopoverClickHandler.alloc().init()
        self._click_handler.popover = self._popover
        self._click_handler.nsstatusitem = nsstatusitem
        self._click_handler.popover_controller = self._popover_controller

        # 设置按钮点击 action
        button.setTarget_(self._click_handler)
        button.setAction_("togglePopover:")

        # 显式重新设置图标（确保自定义点击行为后图标不丢失）
        if self._icon_nsimage:
            nsstatusitem.setImage_(self._icon_nsimage)
            button.setImage_(self._icon_nsimage)
        else:
            icon_path = Path(__file__).parent / "assets" / "menubar_icon.png"
            if icon_path.exists():
                from rumps.rumps import _nsimage_from_file
                img = _nsimage_from_file(str(icon_path), template=True)
                if img:
                    nsstatusitem.setImage_(img)
                    button.setImage_(img)

    # ── 定时刷新 ──────────────────────────────────────────────

    def _refresh_status(self, _):
        """每 15 秒从 history 读最新指标，更新 Popover"""
        latest = _main_mod.history.latest
        if not latest:
            return

        # 注意：不修改菜单栏图标，保持彩色 logo 不变

        # 更新 Popover（仅在显示时）
        if self._popover and self._popover.isShown() and self._popover_controller:
            self._popover_controller.update_metrics()
            self._popover_controller.update_usage()
            self._popover_controller.update_autokill_button()

    def _schedule_usage_refresh(self):
        """使用 Timer 定时刷新 usage 缓存"""
        def _refresh_and_reschedule():
            self._auto_refresh_usage()
            # 刷新完成后重新调度下一次
            if self._usage_refresh_interval > 0:
                self._schedule_usage_refresh()

        timer = threading.Timer(self._usage_refresh_interval, _refresh_and_reschedule)
        timer.daemon = True
        timer.start()

    def _auto_refresh_usage(self):
        """后台自动刷新 usage 缓存"""
        try:
            import requests
            requests.post(f"{self._url}/api/usage/refresh", timeout=60)
        except Exception:
            pass  # 自动刷新失败不影响正常运行


def _kill_stale_processes():
    """启动时清理旧的 AI Guard 进程和占用的端口"""
    import signal

    my_pid = os.getpid()
    port = _main_mod.SERVER_CFG.get("port", 8765)

    # 1. 杀掉占用端口的进程
    try:
        import subprocess
        result = subprocess.run(
            ["lsof", "-ti", f":{port}"],
            capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.strip().split("\n"):
            pid = int(line.strip()) if line.strip() else 0
            if pid and pid != my_pid:
                try:
                    os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
    except Exception:
        pass

    # 2. 杀掉同名旧进程
    try:
        import psutil
        for proc in psutil.process_iter(['pid', 'name']):
            if proc.info['name'] == 'AI Guard' and proc.info['pid'] != my_pid:
                try:
                    proc.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
    except Exception:
        pass


def main():
    _kill_stale_processes()
    AIGuardApp().run()


if __name__ == "__main__":
    main()
