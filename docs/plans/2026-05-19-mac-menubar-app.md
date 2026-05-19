# AI Guard Mac 菜单栏 App 实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将现有 Python/FastAPI 脚本包装成一个 macOS 菜单栏原生 App，用户双击即用，开机自启，无需开终端。

**Architecture:** 使用 `rumps` 库在菜单栏托盘驻留，托盘进程作为宿主启动内置 FastAPI 服务（子线程），点击菜单项打开浏览器 Web UI。使用 `py2app` 打包成独立 `.app`，配合 `launchd` plist 实现开机自启。数据持久化仅用 SQLite 单文件记录告警历史（可选）。

**Tech Stack:** Python 3.10+, rumps 0.4.0, py2app 0.28, FastAPI (已有), psutil (已有), SQLite3 (标准库)

---

## 总体架构说明

```
AI Guard.app
└── MacOS/
    └── AI Guard          ← py2app 打包的可执行文件
        ├── rumps 菜单栏托盘  ← 主线程（事件循环）
        ├── FastAPI 服务     ← 后台线程（原 main.py 逻辑）
        └── Web UI           ← 浏览器打开 http://localhost:8765
```

菜单栏图标点击展开菜单：
- 📊 打开监控面板（浏览器）
- 状态行：内存 XX% · Swap XX%
- ─────────────
- ⚡ 自动终止：关/开
- ─────────────
- 🔔 告警历史（展开子菜单，最近5条）
- ─────────────
- ⚙️ 偏好设置（打开 config.toml）
- 退出 AI Guard

---

## Task 1: 环境准备 + 依赖安装

**Files:**
- Modify: `requirements.txt`
- Create: `requirements-dev.txt`

**Step 1: 安装 rumps 和 py2app**

```bash
pip install rumps==0.4.0
pip install py2app==0.28.8
```

**Step 2: 验证 rumps 可用**

```bash
python3 -c "import rumps; print(rumps.__version__)"
```
Expected: 打印版本号，无报错

**Step 3: 更新 requirements.txt**

在 `requirements.txt` 末尾追加：

```
rumps==0.4.0
```

**Step 4: 创建 requirements-dev.txt（打包工具，不进 App）**

```
py2app==0.28.8
```

**Step 5: Commit**

```bash
git add requirements.txt requirements-dev.txt
git commit -m "feat: add rumps dependency for menubar app"
```

---

## Task 2: 重构入口 — 拆分 FastAPI 启动逻辑

> 目的：让 `main.py` 的 FastAPI 服务可以被外部（rumps App）以函数调用方式启动，而不是只能 `python main.py`。

**Files:**
- Modify: `main.py`（拆出 `start_server()` 函数）

**Step 1: 在 `main.py` 底部，将 uvicorn 启动包装成函数**

在 `main.py` 的 `if __name__ == "__main__":` 块**之前**添加：

```python
def start_server(host: str = None, port: int = None):
    """供外部调用（如 rumps App）的启动函数，在当前线程阻塞运行。"""
    _host = host or SERVER_CFG.get("host", "127.0.0.1")
    _port = port or SERVER_CFG.get("port", 8765)
    print(f"AI Guard 服务启动中 → http://{_host}:{_port}")
    uvicorn.run(app, host=_host, port=_port, log_level="warning")
```

**Step 2: 修改 `if __name__ == "__main__":` 块，调用新函数**

```python
if __name__ == "__main__":
    start_server()
```

**Step 3: 验证原有启动方式仍正常**

```bash
cd "/Users/rocalight/Desktop/All in one/01_PROJECTS/AI Guard"
python main.py &
sleep 2
curl http://localhost:8765/api/metrics
kill %1
```
Expected: 返回 JSON 格式的指标数据

**Step 4: Commit**

```bash
git add main.py
git commit -m "refactor: extract start_server() for external invocation"
```

---

## Task 3: 创建菜单栏 App 主文件

**Files:**
- Create: `app_menubar.py`

**Step 1: 创建 `app_menubar.py`**

```python
"""app_menubar.py — macOS 菜单栏托盘入口"""

import threading
import time
import webbrowser
from pathlib import Path

import rumps

# 延迟导入，避免在 py2app 打包时过早初始化 FastAPI
def _import_server():
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from main import start_server, history, alerter, _latest_processes, _lock, \
                     _autokill_enabled, toggle_autokill_state, SERVER_CFG
    return start_server, history, alerter, _latest_processes, _lock, \
           toggle_autokill_state, SERVER_CFG


class AIGuardApp(rumps.App):
    def __init__(self):
        super().__init__(
            name="AI Guard",
            title="🛡",          # 菜单栏图标文字（可替换为 .icns）
            quit_button=None,    # 自定义退出按钮
        )

        # 延迟导入并启动 FastAPI 服务
        (self._start_server, self._history, self._alerter,
         self._procs_ref, self._lock,
         self._toggle_autokill, self._server_cfg) = _import_server()

        host = self._server_cfg.get("host", "127.0.0.1")
        port = self._server_cfg.get("port", 8765)
        self._url = f"http://{host}:{port}"

        # 在后台线程启动 FastAPI（阻塞调用）
        self._server_thread = threading.Thread(
            target=self._start_server, daemon=True
        )
        self._server_thread.start()

        # 构建菜单
        self._build_menu()

        # 每 2 秒刷新菜单栏状态行
        self._timer = rumps.Timer(self._refresh_status, 2)
        self._timer.start()

    def _build_menu(self):
        self.menu = [
            rumps.MenuItem("📊 打开监控面板", callback=self._open_panel),
            rumps.separator,
            rumps.MenuItem("状态: 启动中…", callback=None),   # key: "状态"
            rumps.separator,
            rumps.MenuItem("⚡ 自动终止: 关", callback=self._toggle_autokill_ui),
            rumps.separator,
            rumps.MenuItem("⚙️ 偏好设置", callback=self._open_config),
            rumps.separator,
            rumps.MenuItem("退出 AI Guard", callback=self._quit),
        ]

    def _open_panel(self, _):
        webbrowser.open(self._url)

    def _open_config(self, _):
        import subprocess
        config_path = Path(__file__).parent / "config.toml"
        subprocess.run(["open", "-t", str(config_path)])

    def _toggle_autokill_ui(self, sender):
        from main import _autokill_enabled
        import main as _main
        _main._autokill_enabled = not _main._autokill_enabled
        state = _main._autokill_enabled
        sender.title = f"⚡ 自动终止: {'开' if state else '关'}"

    def _refresh_status(self, _):
        """每 2 秒从 history 读最新指标，更新菜单栏 title 和状态行"""
        from main import history as _hist
        latest = _hist.latest
        if not latest:
            return

        mem = latest.get("mem_percent", 0)
        swap = latest.get("swap_percent", 0)
        level = latest.get("alert_level", "normal")

        # 菜单栏图标旁的文字
        icons = {"normal": "🛡", "warn": "🟡", "crit": "🔴"}
        self.title = f"{icons.get(level, '🛡')} {mem:.0f}%"

        # 更新菜单中的状态行
        status_item = self.menu.get("状态: 启动中…") or self.menu.get(
            next((k for k in self.menu._menuitem_lookup if k.startswith("状态")), ""), None
        )
        # 简单做法：通过遍历找到 title 包含 "状态" 的项
        for item in self.menu.values():
            if hasattr(item, "title") and "状态" in (item.title or ""):
                item.title = f"状态: 内存 {mem:.0f}% · Swap {swap:.0f}%"
                break

    def _quit(self, _):
        rumps.quit_application()


def main():
    AIGuardApp().run()


if __name__ == "__main__":
    main()
```

**Step 2: 运行一次，验证菜单栏图标出现（不打包，直接跑）**

```bash
cd "/Users/rocalight/Desktop/All in one/01_PROJECTS/AI Guard"
python app_menubar.py
```
Expected:
- 菜单栏出现 `🛡` 图标
- 点击出现菜单项
- 点击「📊 打开监控面板」能打开浏览器 `http://localhost:8765`

**Step 3: 退出后 Commit**

```bash
git add app_menubar.py
git commit -m "feat: add rumps menubar app entry point"
```

---

## Task 4: 修复菜单状态刷新逻辑（rumps API 适配）

> `rumps` 的菜单项查找 API 较为特殊，需要用 `self.menu["key"]` 的方式，key 是初始 title 字符串。

**Files:**
- Modify: `app_menubar.py`

**Step 1: 给状态行菜单项赋一个稳定的 key**

将 `_build_menu` 中状态行改为用变量持有：

```python
def _build_menu(self):
    self._status_item = rumps.MenuItem("状态: 启动中…")
    self._autokill_item = rumps.MenuItem(
        "⚡ 自动终止: 关", callback=self._toggle_autokill_ui
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
```

**Step 2: 简化 `_refresh_status`，直接用实例变量**

```python
def _refresh_status(self, _):
    from main import history as _hist
    import main as _main
    latest = _hist.latest
    if not latest:
        return

    mem   = latest.get("mem_percent", 0)
    swap  = latest.get("swap_percent", 0)
    level = latest.get("alert_level", "normal")

    icons = {"normal": "🛡", "warn": "🟡", "crit": "🔴"}
    self.title = f"{icons.get(level, '🛡')} {mem:.0f}%"
    self._status_item.title = f"状态: 内存 {mem:.0f}% · Swap {swap:.0f}%"
    state = _main._autokill_enabled
    self._autokill_item.title = f"⚡ 自动终止: {'开' if state else '关'}"
```

**Step 3: 验证运行**

```bash
python app_menubar.py
```
Expected: 菜单栏数字每 2 秒更新一次

**Step 4: Commit**

```bash
git add app_menubar.py
git commit -m "fix: use instance vars for rumps menu item references"
```

---

## Task 5: 创建 App 图标

**Files:**
- Create: `assets/icon.png`（1024×1024 PNG）
- Create: `assets/icon.iconset/` 目录（用于生成 .icns）

> 如果没有设计工具，用 Python 生成一个简单的占位图标。

**Step 1: 用 Python 生成占位图标（需要 Pillow）**

```bash
pip install Pillow
```

**Step 2: 创建 `assets/` 目录并生成图标**

```bash
mkdir -p "/Users/rocalight/Desktop/All in one/01_PROJECTS/AI Guard/assets"
```

创建 `make_icon.py`（临时脚本，生成后可删）：

```python
"""make_icon.py — 生成占位 App 图标（深蓝色盾牌样式）"""
from PIL import Image, ImageDraw, ImageFont
import os

SIZE = 1024
img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# 背景圆形
draw.ellipse([40, 40, SIZE-40, SIZE-40], fill="#1a1d27")

# 盾牌轮廓（简化多边形）
shield = [
    (SIZE//2, 80),
    (SIZE-80, 220),
    (SIZE-80, SIZE//2 + 60),
    (SIZE//2, SIZE-80),
    (80, SIZE//2 + 60),
    (80, 220),
]
draw.polygon(shield, fill="#3b82f6")
draw.polygon(shield, outline="#60a5fa", width=12)

# 中间 "G" 字
try:
    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 320)
except:
    font = ImageFont.load_default()
draw.text((SIZE//2, SIZE//2 - 20), "G", font=font, fill="white", anchor="mm")

os.makedirs("assets", exist_ok=True)
img.save("assets/icon.png")
print("✅ assets/icon.png 已生成")
```

```bash
cd "/Users/rocalight/Desktop/All in one/01_PROJECTS/AI Guard"
python make_icon.py
```

**Step 3: 转换为 .icns（macOS 标准格式）**

```bash
mkdir -p assets/icon.iconset
sips -z 16 16     assets/icon.png --out assets/icon.iconset/icon_16x16.png
sips -z 32 32     assets/icon.png --out assets/icon.iconset/icon_16x16@2x.png
sips -z 32 32     assets/icon.png --out assets/icon.iconset/icon_32x32.png
sips -z 64 64     assets/icon.png --out assets/icon.iconset/icon_32x32@2x.png
sips -z 128 128   assets/icon.png --out assets/icon.iconset/icon_128x128.png
sips -z 256 256   assets/icon.png --out assets/icon.iconset/icon_128x128@2x.png
sips -z 256 256   assets/icon.png --out assets/icon.iconset/icon_256x256.png
sips -z 512 512   assets/icon.png --out assets/icon.iconset/icon_256x256@2x.png
sips -z 512 512   assets/icon.png --out assets/icon.iconset/icon_512x512.png
cp assets/icon.png assets/icon.iconset/icon_512x512@2x.png
iconutil -c icns assets/icon.iconset -o assets/icon.icns
echo "✅ assets/icon.icns 生成完成"
```

**Step 4: Commit**

```bash
git add assets/icon.png assets/icon.icns
git commit -m "feat: add app icon assets"
```

---

## Task 6: 创建 py2app 打包配置

**Files:**
- Create: `setup.py`（py2app 打包脚本）

**Step 1: 创建 `setup.py`**

```python
"""setup.py — py2app 打包配置"""
from setuptools import setup

APP = ["app_menubar.py"]
DATA_FILES = [
    ("web",    ["web/index.html"]),
    ("",       ["config.toml"]),
    ("assets", ["assets/icon.icns"]),
]
OPTIONS = {
    "argv_emulation": False,    # rumps 不需要 argv emulation
    "iconfile":       "assets/icon.icns",
    "plist": {
        "CFBundleName":               "AI Guard",
        "CFBundleDisplayName":        "AI Guard",
        "CFBundleIdentifier":         "com.aigard.menubar",
        "CFBundleVersion":            "1.0.0",
        "CFBundleShortVersionString": "1.0.0",
        "LSUIElement":                True,   # 不在 Dock 显示，只在菜单栏
        "NSHighResolutionCapable":    True,
    },
    "packages": [
        "fastapi", "uvicorn", "psutil", "rumps",
        "starlette", "anyio", "pydantic",
    ],
    "excludes": ["tkinter", "test", "distutils"],
}

setup(
    app=APP,
    name="AI Guard",
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
```

**Step 2: 测试打包（开发模式，快速验证）**

```bash
cd "/Users/rocalight/Desktop/All in one/01_PROJECTS/AI Guard"
python setup.py py2app --alias
```

> `--alias` 模式：不复制依赖，直接引用本地包，速度快，用于开发验证

Expected: 生成 `dist/AI Guard.app`，无报错

**Step 3: 运行开发模式 App 验证**

```bash
open "dist/AI Guard.app"
```
Expected: 菜单栏出现图标，功能正常

**Step 4: Commit**

```bash
git add setup.py
git commit -m "feat: add py2app packaging config"
```

---

## Task 7: 完整打包（standalone，可分发）

**Files:**
- Modify: `setup.py`（若需要调整）
- Create: `build.sh`（一键构建脚本）

**Step 1: 清理旧构建产物**

```bash
cd "/Users/rocalight/Desktop/All in one/01_PROJECTS/AI Guard"
rm -rf build dist
```

**Step 2: 正式打包**

```bash
python setup.py py2app
```

> 这步耗时较长（1~3 分钟），会复制所有依赖到 App bundle 内

Expected: 生成 `dist/AI Guard.app`（体积约 100~200 MB）

**Step 3: 运行并测试所有功能**

```bash
open "dist/AI Guard.app"
```

检查清单：
- [ ] 菜单栏图标出现
- [ ] 点击「打开监控面板」能打开浏览器
- [ ] Web UI 显示实时数据
- [ ] 自动终止开关可切换
- [ ] 偏好设置能打开 config.toml
- [ ] 退出菜单项可退出 App

**Step 4: 创建 `build.sh` 一键构建脚本**

```bash
#!/bin/bash
set -e
echo "🔨 清理旧构建..."
rm -rf build dist

echo "📦 开始 py2app 打包..."
python setup.py py2app

echo "✅ 构建完成：dist/AI\ Guard.app"
echo "运行：open dist/AI\ Guard.app"
```

```bash
chmod +x build.sh
```

**Step 5: Commit**

```bash
git add build.sh
git commit -m "feat: add one-click build script"
```

---

## Task 8: 开机自启（launchd plist）

**Files:**
- Create: `scripts/install_autostart.sh`
- Create: `scripts/uninstall_autostart.sh`
- Create: `scripts/com.aigard.menubar.plist`（plist 模板）

**Step 1: 创建 plist 模板**

```bash
mkdir -p "/Users/rocalight/Desktop/All in one/01_PROJECTS/AI Guard/scripts"
```

创建 `scripts/com.aigard.menubar.plist`：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.aigard.menubar</string>
    <key>ProgramArguments</key>
    <array>
        <string>PLACEHOLDER_APP_PATH</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
    <key>StandardErrorPath</key>
    <string>/tmp/aigard.err</string>
    <key>StandardOutPath</key>
    <string>/tmp/aigard.out</string>
</dict>
</plist>
```

**Step 2: 创建安装脚本 `scripts/install_autostart.sh`**

```bash
#!/bin/bash
set -e

APP_PATH="$(cd "$(dirname "$0")/.." && pwd)/dist/AI Guard.app/Contents/MacOS/AI Guard"
PLIST_SRC="$(dirname "$0")/com.aigard.menubar.plist"
PLIST_DST="$HOME/Library/LaunchAgents/com.aigard.menubar.plist"

if [ ! -f "$APP_PATH" ]; then
  echo "❌ 找不到 App：$APP_PATH"
  echo "请先运行 build.sh 打包"
  exit 1
fi

echo "📝 写入 LaunchAgent plist..."
sed "s|PLACEHOLDER_APP_PATH|$APP_PATH|g" "$PLIST_SRC" > "$PLIST_DST"

echo "🔄 加载 LaunchAgent..."
launchctl load "$PLIST_DST"

echo "✅ 开机自启已配置。下次登录时 AI Guard 将自动启动。"
echo "如需立即启动：launchctl start com.aigard.menubar"
```

**Step 3: 创建卸载脚本 `scripts/uninstall_autostart.sh`**

```bash
#!/bin/bash
PLIST_DST="$HOME/Library/LaunchAgents/com.aigard.menubar.plist"

if [ -f "$PLIST_DST" ]; then
  launchctl unload "$PLIST_DST" 2>/dev/null || true
  rm "$PLIST_DST"
  echo "✅ 开机自启已移除"
else
  echo "ℹ️  未找到 LaunchAgent，无需卸载"
fi
```

**Step 4: 赋权并测试安装**

```bash
chmod +x scripts/install_autostart.sh scripts/uninstall_autostart.sh
scripts/install_autostart.sh
```

Expected: 输出"开机自启已配置"

**Step 5: Commit**

```bash
git add scripts/
git commit -m "feat: add launchd autostart install/uninstall scripts"
```

---

## Task 9: SQLite 告警历史（可选，轻量持久化）

> 只记录 warn/crit 告警事件，不存实时指标。单文件 SQLite，零外部依赖。

**Files:**
- Create: `alert_history.py`
- Modify: `main.py`（在 `_monitor_loop` 中调用）

**Step 1: 创建 `alert_history.py`**

```python
"""alert_history.py — SQLite 告警历史记录（仅 warn/crit）"""

import sqlite3
import time
from pathlib import Path

DB_PATH = Path.home() / ".aigard" / "alert_history.db"


def _get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            ts      REAL    NOT NULL,
            level   TEXT    NOT NULL,  -- warn / crit
            reason  TEXT    NOT NULL
        )
    """)
    conn.commit()
    return conn


def record_alert(level: str, reason: str):
    """记录一条告警（非阻塞，忽略写入错误）"""
    if level not in ("warn", "crit"):
        return
    try:
        conn = _get_conn()
        conn.execute(
            "INSERT INTO alerts (ts, level, reason) VALUES (?, ?, ?)",
            (time.time(), level, reason)
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


def get_recent_alerts(limit: int = 20) -> list:
    """读取最近 N 条告警"""
    try:
        conn = _get_conn()
        rows = conn.execute(
            "SELECT ts, level, reason FROM alerts ORDER BY ts DESC LIMIT ?",
            (limit,)
        ).fetchall()
        conn.close()
        return [{"ts": r[0], "level": r[1], "reason": r[2]} for r in rows]
    except Exception:
        return []
```

**Step 2: 在 `main.py` 的 `_monitor_loop` 中集成**

在 `monitor.py` import 附近添加：
```python
from alert_history import record_alert
```

在 `_monitor_loop` 函数的 `alerter.check(m.to_dict())` 一行后面，将：
```python
level = alerter.check(m.to_dict())
```
改为：
```python
level = alerter.check(m.to_dict())
if level in ("warn", "crit"):
    record_alert(level, f"内存 {m.mem_percent:.0f}% / Swap {m.swap_percent:.0f}%")
```

**Step 3: 添加 API 接口（在 `main.py` 中）**

```python
@app.get("/api/alerts/history")
def get_alert_history():
    from alert_history import get_recent_alerts
    return get_recent_alerts(20)
```

**Step 4: 验证**

```bash
python main.py &
sleep 3
curl http://localhost:8765/api/alerts/history
kill %1
```
Expected: 返回 `[]` 或告警列表

**Step 5: Commit**

```bash
git add alert_history.py main.py
git commit -m "feat: add SQLite alert history persistence"
```

---

## Task 10: 更新文档

**Files:**
- Modify: `CLAUDE.md`
- Modify: `docs/plans/2026-05-19-mac-menubar-app.md`（标记完成）

**Step 1: 更新 CLAUDE.md 的目录结构和启动命令**

在 CLAUDE.md 的目录结构中添加新文件，在快速启动中添加：

```bash
# 开发模式运行菜单栏 App
python app_menubar.py

# 打包成 .app
bash build.sh

# 安装开机自启
bash scripts/install_autostart.sh
```

**Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md for menubar app"
```

---

## 快速回顾：改动清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `requirements.txt` | 追加 rumps | 菜单栏库 |
| `requirements-dev.txt` | 新建 | py2app 打包工具 |
| `main.py` | 小改 | 拆出 `start_server()` + 告警历史集成 |
| `app_menubar.py` | 新建 | 菜单栏 App 主体 |
| `setup.py` | 新建 | py2app 打包配置 |
| `build.sh` | 新建 | 一键打包脚本 |
| `alert_history.py` | 新建 | SQLite 告警历史（可选） |
| `assets/icon.png` + `.icns` | 新建 | App 图标 |
| `scripts/` | 新建 | 开机自启安装/卸载脚本 |

## 不需要的东西（YAGNI）

- ❌ 不需要数据库服务（PostgreSQL/MySQL）
- ❌ 不需要 Redis
- ❌ 不需要迁移框架（Alembic 等）
- ❌ 不需要重写 Web UI（现有 HTML 完全够用）
- ❌ 不需要 React/Vue（当前 Vanilla JS 已满足需求）
