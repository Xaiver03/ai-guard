# AI Guard

> Mac AI 开发资源守护工具 — 实时监控 · 分级告警 · 安全进程干预

当你在使用 Claude Code、Codex、Cursor 等 AI 编程 Agent 时，本工具可防止 Mac 内存 / Swap / 磁盘被快速耗尽。以 macOS 菜单栏原生 App 的形式常驻后台，无需打开终端。

## 功能特性

- **实时监控** — 每秒采集内存、Swap、磁盘、CPU 使用率
- **分级告警** — 通过 macOS 原生通知推送 warn / crit 两级告警，Swap 独立冷却时间
- **可视化仪表盘** — 浏览器 Web UI，实时折线图（Chart.js）
- **安全进程干预** — 暂停 / 恢复 / 终止，拒绝强制 SIGKILL
- **进程白名单** — 标记关键进程永不自动终止，支持进程名、命令行关键字、临时 PID
- **所有进程视图** — 类似活动监视器，可查看系统所有进程，默认显示 AI/开发进程
- **书签管理** — 智能分析和管理浏览器书签，支持 AI 相关内容识别
- **菜单栏托盘** — rumps 驱动，支持开机自启，显示 CPU、内存、Swap、磁盘状态
- **告警历史** — SQLite 持久化，随时回查历史事件

## 技术栈

| 层 | 技术 |
|----|------|
| 后端 | Python 3.11+, FastAPI, hypercorn, psutil |
| 前端 | 单文件 HTML + Vanilla JS + Chart.js (CDN) |
| 菜单栏 | rumps 0.4.0 |
| 打包 | py2app 0.28（生成独立 `.app`） |
| 持久化 | SQLite（`~/.aigard/alert_history.db`） |
| 配置 | `config.toml` |

## 快速开始

### 环境要求

- macOS 12+
- Python 3.11+ (推荐使用 pyenv 管理版本)

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
swap_cooldown_sec = 300  # Swap 独立冷却时间（秒）
disk_warn = 85
disk_crit = 95

[processes]
watch_keywords = ["claude", "codex", "cursor", "python"]

[whitelist]
# 进程白名单（永不自动终止）
process_names = []           # 进程名精确匹配
cmdline_keywords = []        # 命令行关键字包含匹配

[server]
port = 8765
```

## API 接口

| Method | Path | 说明 |
|--------|------|------|
| GET | `/api/metrics` | 当前系统指标快照 |
| GET | `/api/stream` | SSE 实时推流（每秒） |
| GET | `/api/processes` | AI 进程列表（含安全评估） |
| GET | `/api/processes/all` | 所有系统进程列表 |
| GET | `/api/alerts/history` | 告警历史（最近 20 条） |
| POST | `/api/processes/{pid}/pause` | 暂停进程（SIGSTOP） |
| POST | `/api/processes/{pid}/resume` | 恢复进程（SIGCONT） |
| POST | `/api/processes/{pid}/kill` | 终止进程（SIGTERM） |
| POST | `/api/processes/batch/kill-safe` | 一键终止所有安全进程 |
| POST | `/api/autokill/toggle` | 切换自动终止开关 |
| GET | `/api/whitelist` | 获取白名单配置 |
| POST | `/api/whitelist/process-name` | 添加进程名到白名单 |
| DELETE | `/api/whitelist/process-name` | 从白名单移除进程名 |
| POST | `/api/whitelist/cmdline-keyword` | 添加命令行关键字到白名单 |
| DELETE | `/api/whitelist/cmdline-keyword` | 从白名单移除命令行关键字 |
| POST | `/api/whitelist/pid` | 添加临时 PID 到白名单 |
| DELETE | `/api/whitelist/pid` | 从白名单移除 PID |

## 项目结构

```
AI Guard/
├── main.py                    # FastAPI 服务 + 后台监控线程
├── app_menubar.py             # 菜单栏 App 入口（rumps）
├── config.toml                # 用户配置
├── setup.py                   # py2app 打包配置
├── build.sh                   # 一键打包脚本
├── aigard/
│   ├── core/
│   │   ├── monitor.py         # 系统指标采集（psutil）
│   │   ├── alerter.py         # 分级告警（macOS 通知）
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
├── assets/                    # App 图标
├── scripts/                   # 开机自启脚本
└── docs/                      # 开发文档
```

## 干预设计原则

不直接 SIGKILL，避免打断正在进行的 AI 任务：

1. `SIGSTOP` — 暂停进程，冻结资源占用
2. 用户在界面确认
3. `SIGTERM` — 优雅退出

随时可通过 `SIGCONT` 恢复，零数据损失。

## License

MIT © Xavier
