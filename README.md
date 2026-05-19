# AI Guard

> Mac AI 开发资源守护工具 — 实时监控 · 分级告警 · 安全进程干预

当你在使用 Claude Code、Codex、Cursor 等 AI 编程 Agent 时，本工具可防止 Mac 内存 / Swap / 磁盘被快速耗尽。以 macOS 菜单栏原生 App 的形式常驻后台，无需打开终端。

## 功能特性

- **实时监控** — 每秒采集内存、Swap、磁盘使用率
- **分级告警** — 通过 macOS 原生通知推送 warn / crit 两级告警
- **可视化仪表盘** — 浏览器 Web UI，实时折线图（Chart.js）
- **安全进程干预** — 暂停 / 恢复 / 终止，拒绝强制 SIGKILL
- **菜单栏托盘** — rumps 驱动，支持开机自启，零感知运行
- **告警历史** — SQLite 持久化，随时回查历史事件

## 技术栈

| 层 | 技术 |
|----|------|
| 后端 | Python 3.10+, FastAPI, uvicorn, psutil |
| 前端 | 单文件 HTML + Vanilla JS + Chart.js (CDN) |
| 菜单栏 | rumps 0.4.0 |
| 打包 | py2app 0.28（生成独立 `.app`） |
| 持久化 | SQLite（`~/.aigard/alert_history.db`） |
| 配置 | `config.toml` |

## 快速开始

### 环境要求

- macOS 12+
- Python 3.10+

### 安装依赖

```bash
pip install -r requirements.txt
```

### 运行方式

```bash
# 方式一：纯后端模式（浏览器访问 http://localhost:8765）
python main.py

# 方式二：菜单栏 App（推荐）
python app_menubar.py
```

### 打包为独立 .app

```bash
pip install -r requirements-dev.txt
bash build.sh
open "dist/AI Guard.app"
```

### 安装开机自启

```bash
bash scripts/install_autostart.sh

# 卸载
bash scripts/uninstall_autostart.sh
```

## 配置

编辑 `config.toml` 调整行为：

```toml
[alert]
memory_warn = 75       # 内存告警阈值（%）
memory_crit = 90
swap_warn = 50
swap_crit = 80
disk_warn = 85
disk_crit = 95

[processes]
watch_keywords = ["claude", "codex", "cursor", "python"]

[server]
port = 8765
```

## API 接口

| Method | Path | 说明 |
|--------|------|------|
| GET | `/api/metrics` | 当前系统指标快照 |
| GET | `/api/stream` | SSE 实时推流（每秒） |
| GET | `/api/processes` | AI 进程列表（含安全评估） |
| GET | `/api/alerts/history` | 告警历史（最近 20 条） |
| POST | `/api/processes/{pid}/pause` | 暂停进程（SIGSTOP） |
| POST | `/api/processes/{pid}/resume` | 恢复进程（SIGCONT） |
| POST | `/api/processes/{pid}/kill` | 终止进程（SIGTERM） |
| POST | `/api/processes/batch/kill-safe` | 一键终止所有安全进程 |
| POST | `/api/autokill/toggle` | 切换自动终止开关 |

## 项目结构

```
AI Guard/
├── main.py              # FastAPI 服务 + 后台监控线程
├── app_menubar.py       # 菜单栏 App 入口（rumps）
├── monitor.py           # 系统指标采集（psutil）
├── alerter.py           # 分级告警（macOS 通知）
├── killer.py            # 安全进程干预
├── advisor.py           # 进程安全评分
├── alert_history.py     # SQLite 告警历史
├── config.toml          # 用户配置
├── setup.py             # py2app 打包配置
├── build.sh             # 一键打包脚本
├── assets/              # App 图标
├── scripts/             # 开机自启脚本
├── web/index.html       # 实时仪表盘
└── docs/                # 开发文档
```

## 干预设计原则

不直接 SIGKILL，避免打断正在进行的 AI 任务：

1. `SIGSTOP` — 暂停进程，冻结资源占用
2. 用户在界面确认
3. `SIGTERM` — 优雅退出

随时可通过 `SIGCONT` 恢复，零数据损失。

## License

MIT © Xavier
