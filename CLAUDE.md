# AI Guard

> Mac AI 开发资源守护工具 — 监控 + 告警 + 安全干预
> **当前阶段：开发为 macOS 菜单栏原生 App**

## 开发流程原则

**每次代码更改后必须完成以下步骤：**

1. **重新打包应用**
   ```bash
   ./build.sh
   ```

2. **安装到本地测试**
   ```bash
   cp -r "dist/AI Guard.app" /Applications/
   open "/Applications/AI Guard.app"
   ```

3. **更新文档**
   - 更新 README.md（如果有新功能或配置变更）
   - 更新 CLAUDE.md（如果有架构或技术栈变更）

4. **Git 提交并推送**
   ```bash
   git add .
   git commit -m "feat: 描述你的更改"
   git push origin main
   ```

5. **验证功能**
   - 打开 Web UI (http://localhost:8765)
   - 测试新功能是否正常工作
   - 检查菜单栏状态显示是否正确

**注意：** 不要跳过任何步骤，确保每次更改都经过完整的测试和发布流程。

## 项目简介

解决使用 Claude Code / Codex / Cursor 等 AI 编程 Agent 时，Mac 内存/Swap/磁盘被快速耗尽的问题。

**核心功能：**
1. 实时监控内存、Swap、磁盘、CPU 压力
2. 分级告警（macOS 原生通知，Swap 独立冷却时间）
3. 可视化仪表盘（浏览器 Web UI，实时折线图）
4. 安全进程干预（暂停/恢复/终止，不强制 kill）
5. 进程白名单（永不自动终止的关键进程）
6. 所有进程视图（类似活动监视器，可查看系统所有进程）
7. 书签管理（智能分析和管理浏览器书签）
8. 菜单栏托盘驻留（rumps），开机自启，显示 CPU/内存/Swap/磁盘状态

## 技术栈

| 层 | 技术 |
|----|------|
| 后端 | Python 3.11+, FastAPI, hypercorn, psutil |
| 前端 | 单文件 HTML + Vanilla JS + Chart.js (CDN) |
| 菜单栏 App | rumps 0.4.0（macOS 菜单栏托盘） |
| 打包 | py2app 0.28（生成独立 .app，可分发） |
| 持久化 | SQLite 单文件（告警历史，存 `~/.aigard/`） |
| 配置 | config.toml |

**重要说明：**
- 使用 Python 3.11（不支持 3.12，因为 py2app 依赖已废弃的 pkg_resources）
- 使用 hypercorn 替代 uvicorn（避免 mypyc 编译模块打包问题）
- 依赖必须安装纯 Python 版本（`--no-binary`），避免编译模块打包失败

## 目录结构

```
AI Guard/
├── main.py                    # FastAPI 服务 + 后台监控线程（含 start_server()）
├── app_menubar.py             # 菜单栏 App 入口（rumps，开发/运行时入口）
├── config.toml                # 用户配置：阈值、监控关键字、白名单
├── setup.py                   # py2app 打包配置
├── build.sh                   # 一键打包脚本
├── requirements.txt           # 运行时依赖（含 rumps）
├── requirements-dev.txt       # 开发依赖（py2app）
├── aigard/
│   ├── core/
│   │   ├── monitor.py         # 系统指标采集（psutil）
│   │   ├── alerter.py         # 分级告警（osascript macOS 通知）
│   │   ├── threads.py         # 后台线程管理
│   │   ├── whitelist.py       # 白名单管理
│   │   └── ...
│   ├── api/
│   │   ├── routes.py          # 主要 API 路由
│   │   ├── whitelist.py       # 白名单 API
│   │   ├── bookmarks.py       # 书签 API
│   │   └── ...
│   ├── ui/
│   │   ├── index.html         # 实时监控仪表盘
│   │   └── bookmarks.html     # 书签管理界面
│   └── bookmarks/             # 书签分析模块
├── assets/
│   ├── icon.png               # App 图标源文件（1024×1024）
│   └── icon.icns              # macOS 图标格式
├── scripts/
│   ├── install_autostart.sh   # 安装开机自启（launchd）
│   ├── uninstall_autostart.sh # 卸载开机自启
│   └── com.aigard.menubar.plist # LaunchAgent plist 模板
├── docs/
│   ├── plans/
│   │   ├── 2026-05-19-mac-menubar-app.md  # 菜单栏 App 实现计划
│   │   └── v1.2.0-feature-planning.md     # v1.2.0 版本规划
│   └── BOOKMARKS_GUIDE.md     # 书签功能使用指南
└── SCORING.md                 # 进程安全评分规则说明
```

## 快速启动

```bash
cd "01_PROJECTS/AI Guard"

# 确保使用 Python 3.11（不支持 3.12）
pyenv local 3.11.15

# 创建虚拟环境并安装依赖
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 方式一：纯后端脚本模式（浏览器打开 http://localhost:8765）
python main.py

# 方式二：菜单栏 App 开发模式（推荐）
python app_menubar.py

# 打包成可分发 .app
bash build.sh

# 安装到 /Applications（替换旧版本）
cp -r "dist/AI Guard.app" /Applications/

# 打开应用
open "/Applications/AI Guard.app"

# 安装开机自启
bash scripts/install_autostart.sh
```

## 打包注意事项

**重要：** 打包前必须确保以下条件：

1. **Python 版本**：必须使用 Python 3.11.x（不支持 3.12）
   ```bash
   pyenv install 3.11.15
   pyenv local 3.11.15
   ```

2. **依赖版本**：
   - setuptools < 70.0.0（避免 pkg_resources 问题）
   - 使用纯 Python 版本的依赖（避免 mypyc 编译模块）
   ```bash
   pip install 'setuptools<70.0.0'
   pip uninstall -y tomli && pip install tomli --no-binary tomli
   ```

3. **打包流程**：
   ```bash
   # 清理旧的打包文件
   rm -rf build dist
   
   # 执行打包
   ./build.sh
   
   # 安装到 /Applications（替换旧版本）
   cp -r "dist/AI Guard.app" /Applications/
   ```

4. **常见问题**：
   - 如果遇到 `ModuleNotFoundError: No module named 'ddc459050edb75a05942__mypyc'`，说明 tomli 使用了编译版本，需要重新安装纯 Python 版本
   - 如果遇到 `RuntimeError: set_wakeup_fd only works in main thread`，说明 ASGI 服务器在子线程中无法设置信号处理器，已在 main.py 中处理

## 菜单栏 App 架构

```
AI Guard.app（菜单栏托盘）
├── rumps 主线程           ← 事件循环，处理菜单点击
├── FastAPI 后台线程       ← 原 main.py 逻辑，localhost:8765
└── Web UI（浏览器）       ← 点击「打开监控面板」触发
```

菜单项：
- 📊 打开监控面板
- 状态：CPU XX% · 内存 XX% · Swap XX% · 磁盘 XX%（每2秒刷新）
- ⚡ 自动终止：开/关（带 Toast 通知）
- 🔪 一键终止安全进程
- ⚙️ 偏好设置（打开 config.toml）
- 退出 AI Guard

## 配置说明

编辑 `config.toml` 可调整：
- `[alert]` — 告警阈值（内存/Swap/磁盘）
- `[processes].watch_keywords` — 被监控的进程关键字
- `[server].port` — 端口号（默认 8765）

## API 接口

| Method | Path | 说明 |
|--------|------|------|
| GET | `/` | 仪表盘页面 |
| GET | `/api/metrics` | 当前系统指标快照 |
| GET | `/api/stream` | SSE 实时推流（每1秒） |
| GET | `/api/processes` | AI 进程列表（含安全评估） |
| GET | `/api/alerts/history` | 告警历史（SQLite，最近20条） |
| POST | `/api/processes/{pid}/pause` | 暂停进程（SIGSTOP） |
| POST | `/api/processes/{pid}/resume` | 恢复进程（SIGCONT） |
| POST | `/api/processes/{pid}/kill` | 终止进程（SIGTERM） |
| POST | `/api/processes/batch/kill` | 批量终止 |
| POST | `/api/processes/batch/pause` | 批量暂停 |
| POST | `/api/processes/batch/kill-safe` | 一键终止所有安全进程 |
| POST | `/api/autokill/toggle` | 切换自动终止开关 |

## 干预设计原则

- **不直接 SIGKILL**，避免工作中断
- 先 `SIGSTOP` 暂停 → 用户在界面确认 → 再 `SIGTERM` 优雅退出
- 可随时 `SIGCONT` 恢复，零损失继续工作

## 数据持久化策略

- **实时指标**：内存环形缓冲区（150点≈2.5分钟），不持久化，重启重新采集
- **告警历史**：SQLite 单文件，存 `~/.aigard/alert_history.db`，只记录 warn/crit 事件
- **不需要**：PostgreSQL、Redis、迁移框架等重型方案

## 当前开发状态

**计划文档**：`docs/plans/2026-05-19-mac-menubar-app.md`

| Task | 内容 | 状态 |
|------|------|------|
| Task 1 | 环境准备 + 依赖安装 | ✅ 已完成 |
| Task 2 | 重构 main.py start_server() | ✅ 已完成 |
| Task 3 | 创建 app_menubar.py | ✅ 已完成 |
| Task 4 | 修复菜单状态刷新逻辑 | ✅ 已完成 |
| Task 5 | 创建 App 图标 | ✅ 已完成 |
| Task 6 | py2app 打包配置 | ✅ 已完成 |
| Task 7 | 完整打包（standalone）| ✅ 已完成 |
| Task 8 | 开机自启（launchd）| ✅ 已完成 |
| Task 9 | SQLite 告警历史（可选）| ✅ 已完成 |
| Task 10 | 更新文档 | ✅ 已完成 |

**完成时间：** 2026-05-19
