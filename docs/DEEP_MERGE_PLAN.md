# AI Guard 深度融合方案

## 融合目标

将 ccusage 的功能**完全融入** AI Guard，形成单一的、统一的 macOS 应用。不是子目录，而是代码级别的深度整合。

## 深度融合后的项目结构

```
AI Guard/
├── 根目录配置
│   ├── main.py                      # FastAPI 主入口（整合所有功能）
│   ├── app_menubar.py               # rumps 菜单栏应用
│   ├── config.toml                  # 统一配置文件
│   ├── setup.py                     # macOS 打包配置
│   ├── build.sh                     # 一键构建脚本
│   ├── requirements.txt             # Python 依赖
│   ├── requirements-dev.txt         # 开发依赖
│   ├── .python-version              # Python 3.11
│   ├── .gitignore
│   ├── README.md
│   └── CLAUDE.md
│
├── aigard/                          # 统一的核心包
│   ├── __init__.py
│   │
│   ├── core/                        # 核心功能（融合）
│   │   ├── __init__.py
│   │   ├── monitor.py               # 系统资源监控
│   │   ├── killer.py                # 进程管理
│   │   ├── alerter.py               # 告警系统
│   │   ├── advisor.py               # 安全评分
│   │   ├── whitelist.py             # 白名单
│   │   ├── threads.py               # 后台线程
│   │   │
│   │   └── usage/                   # Claude 使用统计（新增）
│   │       ├── __init__.py
│   │       ├── loader.py            # JSONL 数据加载器
│   │       ├── calculator.py        # Token 和费用计算
│   │       ├── aggregator.py        # 数据聚合（日/小时/月）
│   │       ├── pricing.py           # 定价逻辑（从 TS 移植）
│   │       └── models.py            # 数据模型
│   │
│   ├── api/                         # FastAPI 路由（融合）
│   │   ├── __init__.py
│   │   ├── routes.py                # 主路由注册
│   │   ├── monitor.py               # 系统监控 API
│   │   ├── processes.py             # 进程管理 API
│   │   ├── usage.py                 # Claude 统计 API（新增）
│   │   ├── bookmarks.py             # 书签 API
│   │   └── whitelist.py             # 白名单 API
│   │
│   ├── bookmarks/                   # 书签分析
│   │   ├── __init__.py
│   │   ├── safari.py
│   │   ├── manager.py
│   │   ├── analyzer.py
│   │   └── ai_config.py
│   │
│   └── ui/                          # 统一前端（完全重写）
│       ├── index.html               # 单页应用（三标签页）
│       │
│       ├── css/                     # 样式系统
│       │   ├── variables.css        # CSS 变量（设计系统）
│       │   ├── reset.css            # 重置样式
│       │   ├── base.css             # 基础样式
│       │   ├── components.css       # 组件样式
│       │   ├── layout.css           # 布局样式
│       │   └── themes.css           # 主题（暗黑模式）
│       │
│       └── js/                      # JavaScript 模块
│           ├── main.js              # 主入口
│           ├── router.js            # 标签页路由
│           ├── api.js               # API 客户端
│           ├── charts.js            # Chart.js 封装
│           ├── utils.js             # 工具函数
│           │
│           ├── pages/               # 页面模块
│           │   ├── monitor.js       # 系统监控页面
│           │   ├── usage.js         # Claude 统计页面
│           │   └── bookmarks.js     # 书签分析页面
│           │
│           └── components/          # UI 组件
│               ├── tabs.js          # 标签页组件
│               ├── card.js          # 卡片组件
│               ├── table.js         # 表格组件
│               ├── chart.js         # 图表组件
│               └── button.js        # 按钮组件
│
├── assets/                          # 资源文件
│   ├── icon.iconset/                # 应用图标
│   └── icons/                       # UI 图标（SVG）
│       ├── monitor.svg
│       ├── chart-line.svg
│       ├── chart-pie.svg
│       ├── cpu.svg
│       ├── memory.svg
│       ├── settings.svg
│       └── ...
│
├── scripts/                         # 工具脚本
│   ├── install_autostart.sh
│   ├── uninstall_autostart.sh
│   └── build_icons.sh               # 图标构建
│
├── docs/                            # 文档
│   ├── plans/
│   ├── DEEP_MERGE_PLAN.md           # 本文档
│   ├── DESIGN_SYSTEM.md             # 设计系统
│   └── API.md                       # API 文档
│
├── tests/                           # 测试（新增）
│   ├── test_monitor.py
│   ├── test_usage.py
│   └── test_api.py
│
├── build/                           # 构建输出
└── dist/                            # macOS .app 分发包
```

## 关键变更：彻底融合

### 1. 代码级融合（不是目录复制）

| 原 ccusage 模块 | 融合到 AI Guard | 实现方式 |
|----------------|----------------|---------|
| `apps/cli/src/data-loader.ts` | `aigard/core/usage/loader.py` | **Python 重写** |
| `apps/cli/src/calculate-cost.ts` | `aigard/core/usage/calculator.py` | **Python 重写** |
| `packages/internal/src/pricing.ts` | `aigard/core/usage/pricing.py` | **Python 重写** |
| `apps/web/src/App.jsx` | `aigard/ui/js/pages/usage.js` | **Vanilla JS 重写** |
| `apps/web/src/App.css` | `aigard/ui/css/` | **CSS 模块化重写** |

### 2. 完全移除 Node.js 依赖

**不再需要：**
- ❌ pnpm workspace
- ❌ TypeScript 编译
- ❌ React
- ❌ Vite
- ❌ Node.js 运行时

**全部使用 Python：**
- ✅ 纯 Python 实现所有逻辑
- ✅ 纯 HTML/CSS/JS 前端（无构建步骤）
- ✅ 单一 py2app 打包流程

### 3. 数据流设计（深度融合）

```
┌─────────────────────────────────────────────────────────────┐
│                    AI Guard.app                             │
│                  (单一 macOS 应用)                           │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              rumps 菜单栏                             │  │
│  │                                                       │  │
│  │  • 系统监控：内存 XX% · Swap XX%                      │  │
│  │  • Claude 统计：今日 XX tokens · $XX                  │  │
│  │  • 打开面板                                           │  │
│  │  • 自动终止：开/关                                    │  │
│  │  • 退出                                               │  │
│  └──────────────────────────────────────────────────────┘  │
│                          │                                  │
│                          ▼                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           FastAPI 后端 (localhost:8765)               │  │
│  │                                                       │  │
│  │  /api/monitor/*    ◄─── aigard.core.monitor          │  │
│  │  /api/processes/*  ◄─── aigard.core.killer           │  │
│  │  /api/usage/*      ◄─── aigard.core.usage (新)       │  │
│  │  /api/bookmarks/*  ◄─── aigard.bookmarks             │  │
│  │                                                       │  │
│  └──────────────────────────────────────────────────────┘  │
│                          │                                  │
│                          ▼                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         Web UI (单页应用，三标签页)                   │  │
│  │                                                       │  │
│  │  ┌────────────┬────────────┬────────────┐           │  │
│  │  │ 系统监控    │ Claude统计  │ 书签分析    │           │  │
│  │  └────────────┴────────────┴────────────┘           │  │
│  │                                                       │  │
│  │  • 统一的 CSS 变量系统                                │  │
│  │  • 统一的组件库                                       │  │
│  │  • 统一的图表样式                                     │  │
│  │  • 无 Emoji，纯 SVG 图标                             │  │
│  │                                                       │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │  数据源（本地文件）    │
              │                       │
              │  • ~/.claude/projects │
              │  • ~/.aigard/*.db     │
              │  • ~/Library/Safari   │
              └───────────────────────┘
```

### 4. API 端点设计（统一）

#### 系统监控
- `GET /api/monitor/metrics` - 当前系统指标
- `GET /api/monitor/stream` - SSE 实时推流
- `GET /api/monitor/history` - 历史数据

#### 进程管理
- `GET /api/processes` - AI 进程列表
- `POST /api/processes/{pid}/pause` - 暂停进程
- `POST /api/processes/{pid}/resume` - 恢复进程
- `POST /api/processes/{pid}/kill` - 终止进程
- `POST /api/processes/autokill/toggle` - 切换自动终止

#### Claude 使用统计（新增，完全 Python 实现）
- `GET /api/usage/summary` - 总览数据
- `GET /api/usage/daily` - 日报数据
- `GET /api/usage/hourly` - 小时报数据
- `GET /api/usage/monthly` - 月报数据
- `GET /api/usage/models` - 模型统计
- `GET /api/usage/trends` - 趋势分析
- `POST /api/usage/refresh` - 刷新数据

#### 书签分析
- `GET /api/bookmarks` - 书签列表
- `POST /api/bookmarks/analyze` - AI 分析

### 5. 配置文件（统一）

```toml
[app]
name = "AI Guard"
version = "1.2.0"

[server]
host = "127.0.0.1"
port = 8765

[monitor]
# 系统监控配置
memory_warn = 80
memory_crit = 90
swap_warn = 50
swap_crit = 70
disk_warn = 85
disk_crit = 95
check_interval = 2

[processes]
# 进程监控配置
watch_keywords = ["claude", "cursor", "codex", "copilot"]
auto_kill = false

[usage]
# Claude 使用统计配置
claude_data_dir = "~/.claude/projects"
cache_ttl = 300
auto_refresh = true
default_currency = "USD"

[bookmarks]
# 书签分析配置
safari_bookmarks_path = "~/Library/Safari/Bookmarks.plist"
ai_analysis_enabled = true

[ui]
# UI 配置
theme = "dark"
default_tab = "monitor"
chart_animation = true
```

### 6. Python 依赖（完整）

```txt
# Web 框架
fastapi==0.104.1
hypercorn==0.15.0

# 系统监控
psutil==5.9.6

# 菜单栏
rumps==0.4.0

# 配置解析
toml==0.10.2

# 数据处理
pandas==2.1.3
numpy==1.26.2

# 日期时间
python-dateutil==2.8.2

# JSON 处理
orjson==3.9.10

# 数据库
sqlite3  # 内置

# 书签解析
plistlib  # 内置

# HTTP 客户端（用于获取定价数据）
httpx==0.25.2
```

### 7. 核心模块实现（Python）

#### aigard/core/usage/loader.py
```python
"""
Claude JSONL 数据加载器
移植自 ccusage 的 data-loader.ts
"""
import json
import os
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

class ClaudeDataLoader:
    def __init__(self, data_dir: str = "~/.claude/projects"):
        self.data_dir = Path(data_dir).expanduser()
    
    def load_all_sessions(self) -> List[Dict[str, Any]]:
        """加载所有会话数据"""
        sessions = []
        
        if not self.data_dir.exists():
            return sessions
        
        for project_dir in self.data_dir.iterdir():
            if not project_dir.is_dir():
                continue
            
            for session_file in project_dir.glob("*.jsonl"):
                sessions.extend(self._parse_jsonl(session_file))
        
        return sessions
    
    def _parse_jsonl(self, file_path: Path) -> List[Dict[str, Any]]:
        """解析 JSONL 文件"""
        entries = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        entry = json.loads(line)
                        entries.append(entry)
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
        
        return entries
```

#### aigard/core/usage/calculator.py
```python
"""
Token 和费用计算器
移植自 ccusage 的 calculate-cost.ts
"""
from typing import Dict, Any, List
from .pricing import PricingManager

class UsageCalculator:
    def __init__(self):
        self.pricing = PricingManager()
    
    def calculate_tokens(self, entry: Dict[str, Any]) -> Dict[str, int]:
        """计算 Token 数量"""
        return {
            'input': entry.get('input_tokens', 0),
            'output': entry.get('output_tokens', 0),
            'cache_creation': entry.get('cache_creation_input_tokens', 0),
            'cache_read': entry.get('cache_read_input_tokens', 0),
            'total': (
                entry.get('input_tokens', 0) +
                entry.get('output_tokens', 0) +
                entry.get('cache_creation_input_tokens', 0) +
                entry.get('cache_read_input_tokens', 0)
            )
        }
    
    def calculate_cost(self, entry: Dict[str, Any]) -> float:
        """计算费用"""
        model = entry.get('model', '')
        tokens = self.calculate_tokens(entry)
        
        return self.pricing.calculate_cost(
            model=model,
            input_tokens=tokens['input'],
            output_tokens=tokens['output'],
            cache_creation_tokens=tokens['cache_creation'],
            cache_read_tokens=tokens['cache_read']
        )
```

#### aigard/core/usage/pricing.py
```python
"""
定价管理器
移植自 ccusage packages/internal/src/pricing.ts
"""
import httpx
from typing import Dict, Optional

class PricingManager:
    def __init__(self):
        self.cache: Dict[str, Dict[str, float]] = {}
        self.fallback_model = "claude-sonnet-4-6"
    
    def get_model_pricing(self, model: str) -> Optional[Dict[str, float]]:
        """获取模型定价"""
        if model in self.cache:
            return self.cache[model]
        
        # 从 LiteLLM 获取定价
        try:
            pricing = self._fetch_from_litellm(model)
            if pricing:
                self.cache[model] = pricing
                return pricing
        except Exception:
            pass
        
        # Fallback 到 Sonnet 4.6 定价
        return self._get_fallback_pricing()
    
    def _fetch_from_litellm(self, model: str) -> Optional[Dict[str, float]]:
        """从 LiteLLM 获取定价"""
        # 实现 LiteLLM API 调用
        pass
    
    def _get_fallback_pricing(self) -> Dict[str, float]:
        """Fallback 定价（Sonnet 4.6）"""
        return {
            'input': 3.0 / 1_000_000,      # $3 per 1M tokens
            'output': 15.0 / 1_000_000,    # $15 per 1M tokens
            'cache_creation': 3.75 / 1_000_000,
            'cache_read': 0.30 / 1_000_000
        }
    
    def calculate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cache_creation_tokens: int,
        cache_read_tokens: int
    ) -> float:
        """计算总费用"""
        pricing = self.get_model_pricing(model)
        if not pricing:
            return 0.0
        
        return (
            input_tokens * pricing['input'] +
            output_tokens * pricing['output'] +
            cache_creation_tokens * pricing['cache_creation'] +
            cache_read_tokens * pricing['cache_read']
        )
```

### 8. 前端架构（完全重写）

#### aigard/ui/index.html
```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Guard</title>
    
    <!-- CSS -->
    <link rel="stylesheet" href="css/variables.css">
    <link rel="stylesheet" href="css/reset.css">
    <link rel="stylesheet" href="css/base.css">
    <link rel="stylesheet" href="css/components.css">
    <link rel="stylesheet" href="css/layout.css">
    <link rel="stylesheet" href="css/themes.css">
    
    <!-- Chart.js -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
</head>
<body class="theme-dark">
    <!-- 顶部导航 -->
    <nav class="nav-container">
        <div class="nav-tabs">
            <button class="nav-tab active" data-tab="monitor">
                <svg class="icon"><!-- monitor icon --></svg>
                <span>系统监控</span>
            </button>
            <button class="nav-tab" data-tab="usage">
                <svg class="icon"><!-- chart icon --></svg>
                <span>Claude 统计</span>
            </button>
            <button class="nav-tab" data-tab="bookmarks">
                <svg class="icon"><!-- bookmark icon --></svg>
                <span>书签分析</span>
            </button>
        </div>
        
        <div class="nav-actions">
            <button class="btn-icon" id="refresh-btn">
                <svg class="icon"><!-- refresh icon --></svg>
            </button>
            <button class="btn-icon" id="settings-btn">
                <svg class="icon"><!-- settings icon --></svg>
            </button>
        </div>
    </nav>
    
    <!-- 标签页内容 -->
    <main class="main-container">
        <div id="monitor-tab" class="tab-content active">
            <!-- 系统监控内容 -->
        </div>
        
        <div id="usage-tab" class="tab-content">
            <!-- Claude 统计内容 -->
        </div>
        
        <div id="bookmarks-tab" class="tab-content">
            <!-- 书签分析内容 -->
        </div>
    </main>
    
    <!-- JavaScript -->
    <script type="module" src="js/main.js"></script>
</body>
</html>
```

#### aigard/ui/css/variables.css
```css
:root {
    /* 配色（基于 ccusage GitHub 暗黑主题）*/
    --bg-primary: #0d1117;
    --bg-secondary: #161b22;
    --bg-card: #1c2128;
    --text-primary: #e6edf3;
    --text-secondary: #8b949e;
    --accent-blue: #58a6ff;
    --accent-green: #3fb950;
    --accent-orange: #d29922;
    --accent-red: #f85149;
    --accent-purple: #bc8cff;
    --border-color: #30363d;
    
    /* 字体 */
    --font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    --font-mono: 'SF Mono', Consolas, 'Liberation Mono', Menlo, monospace;
    
    /* 圆角 */
    --radius-sm: 6px;
    --radius-md: 8px;
    --radius-lg: 12px;
    
    /* 间距 */
    --spacing-xs: 4px;
    --spacing-sm: 8px;
    --spacing-md: 16px;
    --spacing-lg: 24px;
    --spacing-xl: 32px;
    
    /* 阴影 */
    --shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.3);
    --shadow-md: 0 2px 8px rgba(0, 0, 0, 0.3);
    --shadow-lg: 0 4px 16px rgba(0, 0, 0, 0.4);
    
    /* 过渡 */
    --transition-fast: 150ms ease;
    --transition-normal: 250ms ease;
    --transition-slow: 350ms ease;
}
```

### 9. 构建流程（一键打包）

#### build.sh（更新）
```bash
#!/bin/bash
set -e

echo "🚀 开始构建 AI Guard..."

# 1. 清理旧构建
echo "📦 清理旧构建..."
rm -rf build dist

# 2. 检查 Python 版本
echo "🐍 检查 Python 版本..."
python_version=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
if [ "$python_version" != "3.11" ]; then
    echo "❌ 需要 Python 3.11，当前版本: $python_version"
    exit 1
fi

# 3. 安装 Python 依赖
echo "📥 安装 Python 依赖..."
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 4. 运行测试
echo "🧪 运行测试..."
python3 -m pytest tests/ -v

# 5. 打包应用
echo "📦 打包 macOS 应用..."
python3 setup.py py2app

# 6. 验证构建
echo "✅ 验证构建..."
if [ -d "dist/AI Guard.app" ]; then
    echo "✅ 构建成功！"
    echo "📍 应用位置: dist/AI Guard.app"
    
    # 显示应用大小
    app_size=$(du -sh "dist/AI Guard.app" | cut -f1)
    echo "📊 应用大小: $app_size"
else
    echo "❌ 构建失败！"
    exit 1
fi

echo "🎉 构建完成！"
```

### 10. 安装和使用

```bash
# 1. 克隆项目
cd "/Users/rocalight/Desktop/All in one Data/01_PROJECTS/AI Guard"

# 2. 确保使用 Python 3.11
pyenv local 3.11.15

# 3. 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 4. 安装依赖
pip install -r requirements.txt

# 5. 开发模式运行
python3 main.py

# 6. 打包为 .app
./build.sh

# 7. 安装到 /Applications
cp -r "dist/AI Guard.app" /Applications/

# 8. 打开应用
open "/Applications/AI Guard.app"
```

## 总结：深度融合的优势

| 维度 | 融合前（两个项目） | 融合后（单一应用） |
|------|------------------|------------------|
| **技术栈** | Python + TypeScript + React | 纯 Python + Vanilla JS |
| **依赖管理** | pip + pnpm | 仅 pip |
| **构建流程** | py2app + pnpm build + Vite | 单一 py2app |
| **运行时** | Python + Node.js | 仅 Python |
| **应用大小** | ~150MB | ~80MB（预估） |
| **启动速度** | 较慢（需启动 Node） | 快速（纯 Python） |
| **维护成本** | 高（两套代码） | 低（统一代码） |
| **用户体验** | 两个独立工具 | 单一统一应用 |

## 下一步

1. ✅ 完成深度融合方案设计
2. ⏭️ 实施代码迁移（TS → Python）
3. ⏭️ 重写前端 UI（React → Vanilla JS）
4. ⏭️ 统一设计系统
5. ⏭️ 测试和打包
