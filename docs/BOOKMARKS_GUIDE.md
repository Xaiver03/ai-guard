# AI Guard 书签管理功能使用指南

## 概述

AI Guard 现已集成智能书签管理功能，支持多浏览器书签的 AI 分析和整理。

## 功能特性

### 1. 多浏览器支持
- ✅ Chrome
- ✅ Microsoft Edge
- ✅ DIA Browser
- ✅ Quark Browser
- ✅ Safari（需要系统权限）

### 2. 核心功能
- 📊 书签统计分析
- 🔍 智能搜索
- 🤖 AI 驱动的分类建议
- 🧹 问题检测（重复、URL 问题、命名问题等）
- 📤 导出功能（JSON、HTML、CSV）

### 3. AI 功能
- 自动分类建议
- 书签名称优化
- URL 清理（移除追踪参数）

## 前置要求

### 必须安装 Claude Code

书签管理的 AI 功能**依赖 Claude Code 的 API 配置**。确保：

1. 已安装 Claude Code CLI
2. 配置文件 `~/.claude/settings.json` 中包含：
   ```json
   {
     "env": {
       "ANTHROPIC_AUTH_TOKEN": "your-api-key",
       "ANTHROPIC_BASE_URL": "https://api.anthropic.com"
     }
   }
   ```

### 安装依赖

```bash
cd "/Users/rocalight/Desktop/All in one Data/01_PROJECTS/AI Guard"

# 激活虚拟环境
source venv/bin/activate

# 安装新依赖
pip install httpx>=0.27.0
```

## 使用方法

### 1. 启动 AI Guard

```bash
# 开发模式
python app_menubar.py

# 或直接启动服务
python main.py
```

### 2. 访问书签管理

打开浏览器访问：
- 主页：http://localhost:8765/
- 书签管理：http://localhost:8765/bookmarks.html

或在主页点击导航栏的「书签管理」按钮。

### 3. 选择浏览器

在书签管理页面：
1. 页面会自动检测已安装的浏览器
2. 点击浏览器卡片选择要管理的浏览器
3. 系统会自动加载该浏览器的书签

### 4. 查看统计信息

选择浏览器后，会显示：
- 总书签数
- 文件夹数量
- 域名数量

### 5. 分析书签问题

点击「分析」按钮，系统会检测：
- 🔴 重复书签
- 🟡 URL 问题（追踪参数、过长 URL、重定向链接）
- 🟡 命名问题（名称过长、使用 URL 作为名称、特殊字符）
- 🔵 大型文件夹（超过 20 个书签）
- 🔵 未分类书签

### 6. AI 智能分类

点击「AI 分类」按钮：
1. 系统会将书签发送给 Claude API
2. AI 会分析书签内容并提供分类建议
3. 显示推荐的分类方案和整理建议

**注意**：
- 默认分析前 50 个书签（避免 token 消耗过多）
- 需要配置有效的 Claude API key

### 7. 搜索书签

在搜索框中输入关键词：
- 支持搜索书签名称
- 支持搜索 URL
- 支持搜索文件夹名称

### 8. 导出书签

点击导出按钮：
- **JSON 格式**：结构化数据，便于程序处理
- **HTML 格式**：标准书签格式，可导入其他浏览器
- **CSV 格式**：表格数据，便于 Excel 分析

导出文件保存在系统临时目录。

## API 接口

### 浏览器检测
```
GET /api/bookmarks/browsers
```

### 获取书签
```
GET /api/bookmarks/{browser}
```

### 书签统计
```
GET /api/bookmarks/{browser}/stats
```

### 分析书签
```
POST /api/bookmarks/analyze
Body: { "browser": "chrome" }
```

### AI 分类
```
POST /api/bookmarks/categorize
Body: { "browser": "chrome", "max_bookmarks": 50 }
```

### 搜索书签
```
POST /api/bookmarks/search
Body: { "browser": "chrome", "query": "关键词" }
```

### 导出书签
```
POST /api/bookmarks/export
Body: { "browser": "chrome", "format": "json" }
```

### AI 建议名称
```
POST /api/bookmarks/ai/suggest-name
Body: { "url": "https://example.com", "current_name": "Example" }
```

### 清理 URL
```
POST /api/bookmarks/ai/clean-url
Body: { "url": "https://example.com?utm_source=..." }
```

### AI 配置状态
```
GET /api/bookmarks/ai/config
```

## Safari 权限配置

如果需要管理 Safari 书签，需要授予权限：

1. 打开「系统设置」
2. 进入「隐私与安全性」
3. 选择「完全磁盘访问权限」
4. 添加 AI Guard 应用或 Terminal（开发模式）

## 故障排除

### AI 功能不可用

**问题**：页面显示「AI 未配置」

**解决方案**：
1. 检查 `~/.claude/settings.json` 是否存在
2. 确认 `ANTHROPIC_AUTH_TOKEN` 已配置
3. 点击「重新加载配置」按钮

### Safari 书签无法读取

**问题**：提示「权限不足」

**解决方案**：
1. 按照上述「Safari 权限配置」步骤操作
2. 重启 AI Guard

### 书签数量过多导致加载慢

**解决方案**：
- 书签列表默认只显示前 100 个
- 使用搜索功能快速定位
- 考虑导出后在本地处理

## 技术架构

```
AI Guard 书签管理
├── 后端模块 (Python)
│   ├── aigard/bookmarks/manager.py      # 书签管理核心
│   ├── aigard/bookmarks/analyzer.py     # AI 分析器
│   ├── aigard/bookmarks/safari.py       # Safari 支持
│   ├── aigard/bookmarks/ai_config.py    # AI 配置读取
│   └── aigard/api/bookmarks.py          # API 路由
├── 前端界面 (HTML/JS)
│   └── aigard/ui/bookmarks.html         # 书签管理页面
└── 配置来源
    └── ~/.claude/settings.json          # Claude Code 配置
```

## 数据安全

- ✅ 所有书签数据仅在本地处理
- ✅ AI 分类时仅发送书签名称和 URL（不超过 50 个）
- ✅ 不会修改原始书签文件
- ✅ 导出文件保存在本地临时目录

## 未来计划

- [ ] 书签去重功能
- [ ] 批量重命名
- [ ] 跨浏览器书签同步
- [ ] 书签备份和恢复
- [ ] 更多 AI 整理建议

## 反馈与支持

如有问题或建议，请在 AI Guard 项目中提交 Issue。
