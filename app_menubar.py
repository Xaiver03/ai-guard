"""app_menubar.py — macOS 菜单栏托盘入口（rumps）

运行方式：
    python app_menubar.py          # 开发模式
    open "dist/AI Guard.app"       # 打包后

菜单结构：
    📊 打开监控面板
    ─────────────
    状态: 内存 XX% · Swap XX%（每2秒刷新，不可点击）
    ─────────────
    ⚡ 自动终止: 关/开
    ─────────────
    ⚙️ 偏好设置（打开 config.toml）
    ─────────────
    退出 AI Guard
"""

import os
import sys
import threading
import webbrowser
from pathlib import Path

import rumps

# 禁止 main.py 的 on_startup 自动打开浏览器（菜单栏模式下由用户手动点击）
os.environ["AIGARD_NO_BROWSER"] = "1"

# 确保能 import 到同级的 main.py
sys.path.insert(0, str(Path(__file__).parent))

import main as _main_mod


class AIGuardApp(rumps.App):
    def __init__(self):
        super().__init__(
            name="AI Guard",
            title="🛡",       # 菜单栏显示的文字/图标
            quit_button=None,  # 用自定义退出按钮，避免 rumps 默认的英文 Quit
        )

        # 读取服务地址
        host = _main_mod.SERVER_CFG.get("host", "127.0.0.1")
        port = _main_mod.SERVER_CFG.get("port", 8765)
        self._url = f"http://{host}:{port}"

        # 持有菜单项引用，方便后续刷新
        self._status_item = rumps.MenuItem("状态: 启动中…")
        self._autokill_item = rumps.MenuItem(
            "⚡ 自动终止: 关", callback=self._toggle_autokill
        )

        self.menu = [
            rumps.MenuItem("📊 打开监控面板", callback=self._open_panel),
            rumps.separator,
            self._status_item,
            rumps.separator,
            self._autokill_item,
            rumps.separator,
            rumps.MenuItem("⚙️ 偏好设置", callback=self._open_config),
            rumps.separator,
            rumps.MenuItem("退出 AI Guard", callback=self._quit),
        ]

        # 在后台线程启动 FastAPI（阻塞调用，daemon=True 随主进程退出）
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
        config_path = Path(__file__).parent / "config.toml"
        subprocess.run(["open", "-t", str(config_path)], check=False)

    def _toggle_autokill(self, _):
        with _main_mod._lock:
            _main_mod._autokill_enabled = not _main_mod._autokill_enabled
            state = _main_mod._autokill_enabled
        self._autokill_item.title = f"⚡ 自动终止: {'开' if state else '关'}"

    def _quit(self, _):
        rumps.quit_application()

    # ── 定时刷新 ──────────────────────────────────────────────

    def _refresh_status(self, _):
        """每 2 秒从 history 读最新指标，更新菜单栏标题和状态行"""
        latest = _main_mod.history.latest
        if not latest:
            return

        mem   = latest.get("mem_percent", 0)
        swap  = latest.get("swap_percent", 0)
        level = latest.get("alert_level", "normal")

        # 菜单栏图标旁文字
        icons = {"normal": "🛡", "warn": "🟡", "crit": "🔴"}
        self.title = f"{icons.get(level, '🛡')} {mem:.0f}%"

        # 状态行（不可点击）
        self._status_item.title = f"状态: 内存 {mem:.0f}% · Swap {swap:.0f}%"

        # 同步自动终止开关状态（config 可能外部修改）
        state = _main_mod._autokill_enabled
        self._autokill_item.title = f"⚡ 自动终止: {'开' if state else '关'}"


def main():
    AIGuardApp().run()


if __name__ == "__main__":
    main()
