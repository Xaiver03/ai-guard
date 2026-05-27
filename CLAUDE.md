# AI Guard

> Mac AI 开发资源守护工具 — 监控 + 告警 + 安全干预 + 使用统计
> **当前阶段：开发为 macOS 菜单栏原生 App**

## 开发流程原则

**每次代码更改后必须完成以下步骤：**

1. **重新打包应用**（自动包含版本检查）
   ```bash
   ./build.sh
   ```
   
   > 注：`build.sh` 会自动运行 `scripts/check-version.sh` 检查版本一致性

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
8. Claude 使用统计（Token 用量、费用、模型分布、项目分析）
9. 菜单栏托盘驻留（rumps），开机自启，显示 CPU/内存/Swap 状态
10. 自动更新检查（GitHub Releases API）

## 技术栈

| 层 | 技术 |
|----|------|
| 后端 | Python 3.11+, FastAPI, hypercorn, psutil |
| 前端 | 单文件 HTML + Vanilla JS + Chart.js (CDN) |
| 菜单栏 App | rumps 0.4.0（macOS 菜单栏托盘） |
| 打包 | py2app 0.28（生成独立 .app，可分发） |
| 持久化 | SQLite（告警历史 `~/.aigard/alert_history.db`，使用统计缓存 `~/.aigard/usage_cache.db`） |
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
├── alert_history.py           # SQLite 告警历史持久化
├── config.toml                # 用户配置：阈值、监控关键字、白名单、usage
├── setup.py                   # py2app 打包配置
├── build.sh                   # 一键打包脚本（含版本检查）
├── requirements.txt           # 运行时依赖
├── requirements-dev.txt       # 开发依赖（py2app）
├── aigard/
│   ├── core/
│   │   ├── monitor.py         # 系统指标采集（psutil）
│   │   ├── alerter.py         # 分级告警（osascript macOS 通知）
│   │   ├── threads.py         # 后台线程管理
│   │   ├── whitelist.py       # 白名单管理
│   │   ├── advisor.py         # 进程安全评分
│   │   └── usage/             # Claude 使用统计模块
│   │       ├── __init__.py    # 模块导出
│   │       ├── loader.py      # JSONL 数据加载器
│   │       ├── calculator.py  # 费用计算器
│   │       ├── aggregator.py  # 数据聚合（按日/时/模型）
│   │       ├── pricing.py     # 定价管理
│   │       ├── cache.py       # SQLite 缓存
│   │       └── models.py      # 数据模型（UsageEntry 等）
│   ├── api/
│   │   ├── routes.py          # 主要 API 路由（含缓存机制）
│   │   ├── whitelist.py       # 白名单 API
│   │   ├── bookmarks.py       # 书签 API
│   │   └── usage.py           # Claude 使用统计 API
│   ├── ui/
│   │   ├── index.html         # 实时监控仪表盘
│   │   ├── bookmarks.html     # 书签管理界面
│   │   ├── usage.html         # Claude 使用统计界面
│   │   └── css/               # 共享样式
│   ├── bookmarks/             # 书签分析模块
│   │   ├── manager.py         # 书签管理器
│   │   ├── analyzer.py        # 书签分析
│   │   ├── safari.py          # Safari 书签读取
│   │   └── ai_config.py       # AI 配置
│   └── updater.py             # 自动更新检查（GitHub Releases API）
├── assets/
│   ├── icon.png               # App 图标源文件（1024×1024）
│   └── icon.icns              # macOS 图标格式
├── scripts/
│   ├── check-version.sh       # 版本一致性检查（build.sh 自动调用）
│   ├── install_autostart.sh   # 安装开机自启（launchd）
│   ├── uninstall_autostart.sh # 卸载开机自启
│   └── com.aigard.menubar.plist # LaunchAgent plist 模板
├── docs/
│   ├── distribution.md        # 分发指南（签名、公证、发布、付费支持）
│   └── plans/
│       └── 2026-05-19-mac-menubar-app.md  # 菜单栏 App 实现计划
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

## 打包与分发

**详细指南：** 参见 [docs/distribution.md](docs/distribution.md)

**快速打包：**
```bash
./build.sh  # 自动版本检查 + py2app 打包
```

**签名与公证：**
- 需要 Apple Developer 账号（$99/年）
- 使用 Developer ID Application 证书签名
- 通过 Apple 公证后用户可直接安装，无需手动绕过安全检查
- 详见 [docs/distribution.md#签名与公证](docs/distribution.md#签名与公证)

**发布到 GitHub Release：**
```bash
gh release create v1.1.3 "dist/AI-Guard-v1.1.3.dmg" \
  --title "AI Guard v1.1.3" \
  --notes "Release notes..."
```

**付费支持：**
- GitHub Sponsors: $3-30（推荐）
- 支付宝/微信打赏
- 爱发电赞助
- 详见 [docs/distribution.md#付费支持](docs/distribution.md#付费支持)

## 菜单栏 App 架构

```
AI Guard.app（菜单栏托盘）
├── rumps 主线程           ← 事件循环，处理菜单点击
├── FastAPI 后台线程       ← 原 main.py 逻辑，localhost:8765
└── Web UI（浏览器）       ← 点击菜单项触发
```

菜单项：
- 📊 打开监控面板
- 📈 Claude 使用统计
- 状态：CPU XX% · 内存 XX% · Swap XX%（每2秒刷新，根据告警等级动态调整显示）
- 🔪 一键终止安全进程
- ⚡ 自动终止：开/关（带 Toast 通知）
- 🔄 检查更新
- ⚙️ 偏好设置（打开 config.toml）
- 退出 AI Guard

## 配置说明

编辑 `config.toml` 可调整：
- `[alert]` — 告警阈值（内存/Swap/磁盘）
- `[processes].watch_keywords` — 被监控的进程关键字
- `[whitelist]` — 进程白名单（进程名、命令行关键字、PID）
- `[server].port` — 端口号（默认 8765）
- `[usage]` — Claude 使用统计配置（数据目录、缓存 TTL）

## API 接口

### 监控与系统

| Method | Path | 说明 |
|--------|------|------|
| GET | `/` | 仪表盘页面 |
| GET | `/bookmarks.html` | 书签管理页面 |
| GET | `/usage.html` | Claude 使用统计页面 |
| GET | `/api/metrics` | 当前系统指标快照 |
| GET | `/api/history` | 历史指标数据 |
| GET | `/api/stream` | SSE 实时推流（每1秒） |
| GET | `/api/processes` | AI 进程列表（含安全评估，60秒缓存） |
| GET | `/api/processes/all` | 所有进程列表（60秒缓存） |
| GET | `/api/alerts/history` | 告警历史（SQLite，最近20条） |

### 进程干预

| Method | Path | 说明 |
|--------|------|------|
| POST | `/api/processes/{pid}/pause` | 暂停进程（SIGSTOP） |
| POST | `/api/processes/{pid}/resume` | 恢复进程（SIGCONT） |
| POST | `/api/processes/{pid}/kill` | 终止进程（SIGTERM） |
| POST | `/api/processes/batch/kill` | 批量终止 |
| POST | `/api/processes/batch/pause` | 批量暂停 |
| POST | `/api/processes/batch/kill-safe` | 一键终止所有安全进程 |
| POST | `/api/autokill/toggle` | 切换自动终止开关 |
| GET | `/api/autokill/status` | 获取自动终止状态 |

### Claude 使用统计

| Method | Path | 说明 |
|--------|------|------|
| GET | `/api/usage/summary` | 使用统计总览（支持日期范围/预设） |
| GET | `/api/usage/daily` | 每日使用统计 |
| GET | `/api/usage/hourly` | 每小时使用统计 |
| GET | `/api/usage/monthly` | 每月使用统计 |
| GET | `/api/usage/models` | 模型使用统计 |
| GET | `/api/usage/projects` | 项目列表 |
| GET | `/api/usage/pricing` | 获取定价配置 |
| POST | `/api/usage/pricing` | 更新定价配置 |
| POST | `/api/usage/refresh` | 刷新数据（重新解析 JSONL） |

### 缓存与更新

| Method | Path | 说明 |
|--------|------|------|
| GET | `/api/cache/stats` | 缓存统计信息 |
| POST | `/api/cache/clear` | 清除所有缓存 |
| GET | `/api/update/check` | 检查更新 |
| GET | `/api/update/current-version` | 获取当前版本 |

## 干预设计原则

- **不直接 SIGKILL**，避免工作中断
- 先 `SIGSTOP` 暂停 → 用户在界面确认 → 再 `SIGTERM` 优雅退出
- 可随时 `SIGCONT` 恢复，零损失继续工作

## 数据持久化策略

- **实时指标**：内存环形缓冲区（150点约2.5分钟），不持久化，重启重新采集
- **告警历史**：SQLite 单文件，存 `~/.aigard/alert_history.db`，只记录 warn/crit 事件
- **Claude 使用统计**：SQLite 缓存，存 `~/.aigard/usage_cache.db`，聚合后的日/小时数据（约 132KB，远小于原始 JSONL 的 175MB 内存占用）
- **不需要**：PostgreSQL、Redis、迁移框架等重型方案

## ccusage 深度融合说明

原 ccusage 项目（TypeScript/React）已被完全融合到 AI Guard 中：

**融合方式：代码级完全重写（非子目录引用）**
- TypeScript 数据加载逻辑 -> `aigard/core/usage/loader.py`（Python 重写）
- TypeScript 费用计算 -> `aigard/core/usage/calculator.py` + `pricing.py`（Python 重写）
- React Web Dashboard -> `aigard/ui/usage.html`（Vanilla JS 重写）
- pnpm workspace -> 不再需要 Node.js 运行时

**数据源**：直接读取 `~/.claude/projects/{project}/{sessionId}.jsonl`
- 解析 `type: "assistant"` 记录中的 `message.usage` 和 `message.model` 字段
- 提取 input_tokens, output_tokens, cache_creation_input_tokens, cache_read_input_tokens

**缓存策略**：首次启动解析全量 JSONL -> 聚合后存入 SQLite -> 后续直接从 SQLite 读取
- 首次加载：约 10 秒（解析 16.5 万条记录）
- 后续请求：毫秒级（从 SQLite 读取 31 天 + 448 小时聚合数据）
- 手动刷新：POST `/api/usage/refresh` 重新解析

**设计系统：以 ccusage 的 GitHub Dark 主题为基准**
- 暗色/亮色双主题支持
- 统一配色：#0d1117 背景、#58a6ff 强调色、#30363d 边框
- 统一字体：-apple-system, 'Segoe UI', 'Noto Sans'
- 统一圆角：12px 卡片、8px 按钮
- 无 Emoji，使用 SVG 图标

- **实时指标**：内存环形缓冲区（150点≈2.5分钟），不持久化，重启重新采集
- **告警历史**：SQLite 单文件，存 `~/.aigard/alert_history.db`，只记录 warn/crit 事件
- **使用统计缓存**：SQLite 单文件，存 `~/.aigard/usage_cache.db`，聚合后的日/时数据
- **进程列表缓存**：内存缓存（60秒 TTL），减少 CPU 占用
- **不需要**：PostgreSQL、Redis、迁移框架等重型方案

## Claude 使用统计模块

**数据源：** `~/.claude/projects/*/**.jsonl`（Claude Code 会话日志）

**数据流：**
1. `ClaudeDataLoader` 扫描 JSONL 文件，解析 assistant 类型记录中的 usage 数据
2. `UsageCalculator` + `PricingManager` 计算每条记录的费用
3. `UsageAggregator` 按日/时/模型聚合数据
4. `UsageCache` (SQLite) 缓存聚合结果，避免重复计算
5. API 层提供 REST 接口，前端 usage.html 展示图表

**支持的模型定价：** claude-sonnet-4, claude-opus-4, claude-haiku-3.5 等

**配置：**
```toml
[usage]
claude_data_dir = "~/.claude"  # Claude 数据目录
cache_ttl = 300                # 缓存过期时间（秒）
```
