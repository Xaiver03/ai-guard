# AI Guard + ccusage 项目合并方案

## 合并目标

将 ccusage（Claude 使用统计）整合到 AI Guard 项目中，形成统一的开发者工具套件。

## 合并后的项目结构

```
AI Guard/
├── 根目录配置
│   ├── main.py                      # FastAPI 主入口
│   ├── app_menubar.py               # rumps 菜单栏应用
│   ├── config.toml                  # 统一配置文件
│   ├── setup.py                     # macOS 打包配置
│   ├── build.sh                     # 构建脚本
│   ├── requirements.txt             # Python 依赖
│   ├── requirements-dev.txt         # Python 开发依赖
│   ├── package.json                 # Node.js 依赖（新增）
│   ├── pnpm-workspace.yaml          # pnpm workspace 配置（新增）
│   ├── .python-version              # Python 3.11
│   ├── .gitignore
│   ├── README.md
│   └── CLAUDE.md
│
├── aigard/                          # Python 核心包
│   ├── __init__.py
│   ├── core/                        # 系统监控核心
│   │   ├── __init__.py
│   │   ├── monitor.py               # 系统资源监控
│   │   ├── killer.py                # 进程管理
│   │   ├── alerter.py               # 告警系统
│   │   ├── advisor.py               # 安全评分
│   │   ├── whitelist.py             # 白名单
│   │   ├── threads.py               # 后台线程
│   │   └── ccusage.py               # ccusage 数据解析（新增）
│   │
│   ├── api/                         # FastAPI 路由
│   │   ├── __init__.py
│   │   ├── routes.py                # 系统监控 API
│   │   ├── bookmarks.py             # 书签 API
│   │   ├── whitelist.py             # 白名单 API
│   │   └── ccusage.py               # Claude 统计 API（新增）
│   │
│   ├── bookmarks/                   # 书签分析
│   │   ├── __init__.py
│   │   ├── safari.py
│   │   ├── manager.py
│   │   ├── analyzer.py
│   │   └── ai_config.py
│   │
│   └── ui/                          # 前端界面（统一）
│       ├── index.html               # 主页面（双标签页）
│       ├── bookmarks.html           # 书签页面
│       ├── css/                     # 样式文件（新增）
│       │   ├── variables.css        # CSS 变量（设计系统）
│       │   ├── base.css             # 基础样式
│       │   ├── components.css       # 组件样式
│       │   └── pages.css            # 页面样式
│       └── js/                      # JavaScript 模块（新增）
│           ├── monitor.js           # 系统监控逻辑
│           ├── ccusage.js           # Claude 统计逻辑
│           ├── charts.js            # Chart.js 封装
│           └── utils.js             # 工具函数
│
├── ccusage/                         # ccusage 核心逻辑（新增）
│   ├── cli/                         # CLI 工具（保留）
│   │   ├── src/
│   │   │   ├── index.ts
│   │   │   ├── data-loader.ts       # JSONL 数据加载
│   │   │   ├── calculate-cost.ts    # 成本计算
│   │   │   ├── commands/            # CLI 命令
│   │   │   └── _*.ts                # 工具函数
│   │   ├── package.json
│   │   └── tsconfig.json
│   │
│   ├── packages/                    # 共享包（保留）
│   │   ├── internal/                # 定价、日志等
│   │   │   ├── src/
│   │   │   │   ├── pricing.ts
│   │   │   │   ├── format.ts
│   │   │   │   └── logger.ts
│   │   │   └── package.json
│   │   │
│   │   └── terminal/                # 终端 UI
│   │       ├── src/
│   │       └── package.json
│   │
│   └── scripts/                     # 数据生成脚本（新增）
│       └── generate_data.py         # Python 调用 TS 生成 JSON
│
├── assets/                          # 资源文件
│   ├── icon.iconset/                # 应用图标
│   └── icons/                       # UI 图标（新增，SVG）
│       ├── monitor.svg
│       ├── chart.svg
│       ├── settings.svg
│       └── ...
│
├── scripts/                         # 脚本工具
│   ├── install_autostart.sh
│   ├── uninstall_autostart.sh
│   └── build_ccusage.sh             # 构建 ccusage 数据（新增）
│
├── docs/                            # 文档
│   ├── plans/
│   ├── BOOKMARKS_GUIDE.md
│   ├── PROJECT_MERGE_PLAN.md        # 本文档
│   └── DESIGN_SYSTEM.md             # 设计系统文档（待创建）
│
├── build/                           # 构建输出
├── dist/                            # macOS .app 分发包
└── node_modules/                    # Node.js 依赖
```

## 关键变更

### 1. 目录结构变更

| 变更类型 | 说明 |
|---------|------|
| **新增** `ccusage/` | 将 ccusage 项目作为子目录整合，保留 CLI 和共享包 |
| **新增** `aigard/core/ccusage.py` | Python 模块，解析 Claude JSONL 数据 |
| **新增** `aigard/api/ccusage.py` | FastAPI 路由，提供 Claude 统计 API |
| **重构** `aigard/ui/` | 拆分为 css/ 和 js/ 子目录，模块化前端代码 |
| **新增** `assets/icons/` | SVG 图标库，替换所有 Emoji |
| **新增** `package.json` | 根目录 Node.js 配置，管理 ccusage 依赖 |

### 2. 技术栈整合

| 层级 | 技术 | 说明 |
|------|------|------|
| **后端** | Python 3.11 + FastAPI | 主服务，提供统一 API |
| **前端** | HTML + Vanilla JS + Chart.js | 统一为纯 JS，移除 React |
| **数据处理** | TypeScript (ccusage CLI) | 保留 TS 逻辑，Python 调用生成 JSON |
| **菜单栏** | rumps | macOS 原生菜单栏 |
| **打包** | py2app | 打包为 .app |

### 3. 数据流设计

```
┌─────────────────────────────────────────────────────────────┐
│                      AI Guard.app                           │
│                                                             │
│  ┌──────────────┐         ┌──────────────┐                │
│  │  rumps 菜单栏 │         │ FastAPI 后端  │                │
│  │              │         │              │                │
│  │  - 系统监控   │◄────────┤  /api/metrics │                │
│  │  - Claude统计 │         │  /api/ccusage │                │
│  │  - 打开面板   │         │  /api/stream  │                │
│  └──────────────┘         └───────┬──────┘                │
│                                   │                        │
│                          ┌────────▼────────┐              │
│                          │  aigard.core    │              │
│                          │                 │              │
│                          │  - monitor.py   │              │
│                          │  - ccusage.py   │◄─────┐       │
│                          └─────────────────┘      │       │
│                                                    │       │
│  ┌─────────────────────────────────────────┐     │       │
│  │         Web UI (localhost:8765)         │     │       │
│  │                                         │     │       │
│  │  ┌──────────┐  ┌──────────────────┐   │     │       │
│  │  │ 系统监控  │  │  Claude 使用统计  │   │     │       │
│  │  │          │  │                  │   │     │       │
│  │  │ - 内存   │  │ - Token 趋势     │   │     │       │
│  │  │ - Swap   │  │ - 费用统计       │   │     │       │
│  │  │ - 进程   │  │ - 模型分布       │   │     │       │
│  │  └──────────┘  └──────────────────┘   │     │       │
│  └─────────────────────────────────────────┘     │       │
│                                                    │       │
└────────────────────────────────────────────────────┼───────┘
                                                     │
                                                     │
                                          ┌──────────▼──────────┐
                                          │  ccusage CLI (TS)   │
                                          │                     │
                                          │  - data-loader.ts   │
                                          │  - calculate-cost.ts│
                                          │                     │
                                          │  读取 JSONL 文件     │
                                          │  ~/.claude/projects/│
                                          └─────────────────────┘
```

### 4. API 端点设计

#### 系统监控 API（已有）
- `GET /api/metrics` - 当前系统指标
- `GET /api/stream` - SSE 实时推流
- `GET /api/processes` - AI 进程列表
- `POST /api/processes/{pid}/kill` - 终止进程

#### Claude 统计 API（新增）
- `GET /api/ccusage/daily` - 日报数据
- `GET /api/ccusage/hourly` - 小时报数据
- `GET /api/ccusage/monthly` - 月报数据
- `GET /api/ccusage/models` - 模型统计
- `GET /api/ccusage/refresh` - 刷新数据（调用 TS CLI）

### 5. 前端架构

#### 统一的 index.html 结构
```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>AI Guard</title>
    <link rel="stylesheet" href="css/variables.css">
    <link rel="stylesheet" href="css/base.css">
    <link rel="stylesheet" href="css/components.css">
    <link rel="stylesheet" href="css/pages.css">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
    <!-- 顶部导航 -->
    <nav class="nav-tabs">
        <button class="nav-tab active" data-tab="monitor">系统监控</button>
        <button class="nav-tab" data-tab="ccusage">Claude 统计</button>
        <button class="nav-tab" data-tab="bookmarks">书签分析</button>
    </nav>

    <!-- 标签页内容 -->
    <div id="monitor-tab" class="tab-content active">
        <!-- 系统监控内容 -->
    </div>

    <div id="ccusage-tab" class="tab-content">
        <!-- Claude 统计内容 -->
    </div>

    <div id="bookmarks-tab" class="tab-content">
        <!-- 书签分析内容 -->
    </div>

    <script type="module" src="js/monitor.js"></script>
    <script type="module" src="js/ccusage.js"></script>
    <script type="module" src="js/utils.js"></script>
</body>
</html>
```

## 实施步骤

### Phase 1: 目录结构调整
1. 在 AI Guard 根目录创建 `ccusage/` 子目录
2. 复制 ccusage 的 `cli/` 和 `packages/` 到新目录
3. 创建 `aigard/ui/css/` 和 `aigard/ui/js/` 目录
4. 创建 `assets/icons/` 目录

### Phase 2: Python 后端集成
1. 创建 `aigard/core/ccusage.py` - 数据解析模块
2. 创建 `aigard/api/ccusage.py` - API 路由
3. 在 `main.py` 中注册新路由
4. 创建 `ccusage/scripts/generate_data.py` - 数据生成脚本

### Phase 3: 前端重构
1. 将 ccusage 的 React 组件改写为 Vanilla JS
2. 统一 CSS 变量（基于 ccusage 的设计规范）
3. 创建标签页切换逻辑
4. 移除所有 Emoji，使用 SVG 图标

### Phase 4: 菜单栏集成
1. 在 `app_menubar.py` 中添加「Claude 统计」菜单项
2. 点击时打开 Web UI 并切换到对应标签页
3. 更新菜单栏状态显示

### Phase 5: 构建和测试
1. 更新 `build.sh` 脚本
2. 测试 macOS .app 打包
3. 验证所有功能正常

## 配置文件整合

### config.toml（扩展）
```toml
[server]
host = "127.0.0.1"
port = 8765

[alert]
memory_warn = 80
memory_crit = 90
swap_warn = 50
swap_crit = 70

[processes]
watch_keywords = ["claude", "cursor", "codex"]

[ccusage]
# Claude 数据目录
claude_data_dir = "~/.claude/projects"
# 数据刷新间隔（秒）
refresh_interval = 300
# 是否启用自动刷新
auto_refresh = true
```

### package.json（新增）
```json
{
  "name": "ai-guard",
  "version": "1.2.0",
  "private": true,
  "workspaces": [
    "ccusage/cli",
    "ccusage/packages/*"
  ],
  "scripts": {
    "ccusage:build": "cd ccusage/cli && pnpm build",
    "ccusage:generate": "python3 ccusage/scripts/generate_data.py"
  },
  "devDependencies": {
    "typescript": "^5.0.0"
  }
}
```

## 依赖管理

### Python 依赖（requirements.txt）
```
fastapi==0.104.1
hypercorn==0.15.0
psutil==5.9.6
rumps==0.4.0
toml==0.10.2
```

### Node.js 依赖（通过 pnpm workspace 管理）
- ccusage/cli 的依赖保持不变
- ccusage/packages 的依赖保持不变

## 数据持久化

### SQLite 数据库（扩展）
```
~/.aigard/
├── alert_history.db      # 告警历史
├── ccusage_cache.db      # ccusage 数据缓存（新增）
└── config.toml           # 用户配置
```

## 图标资源

### 需要的 SVG 图标
- monitor.svg - 系统监控
- chart-line.svg - 趋势图
- chart-pie.svg - 饼图
- cpu.svg - CPU
- memory.svg - 内存
- disk.svg - 磁盘
- process.svg - 进程
- settings.svg - 设置
- refresh.svg - 刷新
- calendar.svg - 日历
- dollar.svg - 费用

图标来源：Heroicons 或 Lucide Icons

## 下一步

完成项目结构合并后，进入设计系统统一阶段：
1. 创建 `docs/DESIGN_SYSTEM.md` - 设计系统文档
2. 实现统一的 CSS 变量系统
3. 重写前端 UI（移除 React，统一为 Vanilla JS）
4. 确保视觉一致性
