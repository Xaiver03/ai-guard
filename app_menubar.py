"""app_menubar.py — macOS 菜单栏托盘入口（rumps + SF Symbols）

运行方式：
    python app_menubar.py          # 开发模式
    open "dist/AI Guard.app"       # 打包后

菜单栏图标：SF Symbol 模板图片（自动适配深色/浅色模式）
    正常：shield.fill
    警告：exclamationmark.triangle.fill
    危险：xmark.shield.fill
"""

import os
import sys
import tempfile
import threading
import webbrowser
from pathlib import Path

import rumps
from AppKit import NSImage

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
        return None

    img = img.copy()
    img.setSize_((size, size))
    img.setTemplate_(True)

    # 导出为 PNG
    from AppKit import NSBitmapImageRep, NSPNGFileType
    img.lockFocus()
    rep = NSBitmapImageRep.alloc().initWithFocusedViewRect_(
        ((0, 0), (size, size))
    )
    img.unlockFocus()
    png_data = rep.representationUsingType_properties_(NSPNGFileType, None)
    png_data.writeToFile_atomically_(str(cache_path), True)
    return str(cache_path)


# 三种状态图标
_SYMBOLS = {
    "normal": "shield.fill",
    "warn":   "exclamationmark.triangle.fill",
    "crit":   "xmark.shield.fill",
}


class AIGuardApp(rumps.App):
    def __init__(self):
        super().__init__(
            name="AI Guard",
            title=None,        # 不显示文字，纯图标
            icon=_sf_symbol_to_png(_SYMBOLS["normal"]),
            template=True,     # 模板图片：系统自动处理深色/浅色
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

        # 持有菜单项引用
        self._status_item = rumps.MenuItem("状态: 启动中...")
        self._autokill_item = rumps.MenuItem(
            "自动终止: 关", callback=self._toggle_autokill
        )

        self.menu = [
            rumps.MenuItem("打开监控面板", callback=self._open_panel),
            rumps.separator,
            self._status_item,
            rumps.separator,
            self._autokill_item,
            rumps.separator,
            rumps.MenuItem("偏好设置", callback=self._open_config),
            rumps.separator,
            rumps.MenuItem("退出 AI Guard", callback=self._quit),
        ]

        # 在后台线程启动 FastAPI
        self._server_thread = threading.Thread(
            target=_main_mod.start_server, daemon=True
        )
        self._server_thread.start()

        # 每 2 秒刷新菜单栏状态
        self._timer = rumps.Timer(self._refresh_status, 2)
        self._timer.start()

    # ── 菜单回调 ──────────────────────────────────────────────

    def _open_panel(self, _):
        webbrowser.open(self._url)

    def _open_config(self, _):
        import subprocess
        exe = Path(sys.executable)
        resources = exe.parent.parent / "Resources"
        config_path = resources / "config.toml" if (resources / "config.toml").exists() \
                      else Path(__file__).parent / "config.toml"
        subprocess.run(["open", "-t", str(config_path)], check=False)

    def _toggle_autokill(self, _):
        with _main_mod._lock:
            _main_mod._autokill_enabled = not _main_mod._autokill_enabled
            state = _main_mod._autokill_enabled
        self._autokill_item.title = f"自动终止: {'开' if state else '关'}"

    def _quit(self, _):
        rumps.quit_application()

    # ── 定时刷新 ──────────────────────────────────────────────

    def _refresh_status(self, _):
        """每 2 秒从 history 读最新指标，更新菜单栏图标和状态行"""
        latest = _main_mod.history.latest
        if not latest:
            return

        mem   = latest.get("mem_percent", 0)
        swap  = latest.get("swap_percent", 0)
        level = latest.get("alert_level", "normal")

        # 仅在等级变化时切换图标
        if level != self._last_level:
            symbol_name = _SYMBOLS.get(level, _SYMBOLS["normal"])
            icon_path = _sf_symbol_to_png(symbol_name)
            if icon_path:
                self.icon = icon_path
            self._last_level = level

        # 状态行
        self._status_item.title = f"状态: 内存 {mem:.0f}% / Swap {swap:.0f}%"

        # 同步自动终止开关
        state = _main_mod._autokill_enabled
        self._autokill_item.title = f"自动终止: {'开' if state else '关'}"


def main():
    AIGuardApp().run()


if __name__ == "__main__":
    main()
