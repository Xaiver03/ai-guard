# AI Guard 轻量核心 + 按需加载架构优化计划

**日期：** 2026-05-27  
**目标：** 实现"轻量核心常驻 + 重量级功能按需加载"的架构，同时扩展为 AI 开发者工作台

---

## 一、核心设计原则

### 1.1 轻量级核心（常驻内存，< 50MB）

**必须保留：**
- ✅ 菜单栏 App（rumps）
- ✅ 资源监控线程（CPU/内存/Swap/磁盘）
- ✅ 告警通知（macOS 原生通知）
- ✅ 最小 API 服务（仅提供数据接口）

**优化策略：**
- 懒加载重量级模块（书签、使用统计）
- 减少不必要的后台任务
- 优化菜单栏刷新频率（从 2 秒改为 5 秒）
- 缓存今日使用统计（避免每次刷新都解析 JSONL）

### 1.2 重量级功能（按需加载，浏览器打开）

**已有功能：**
- ✅ 监控仪表盘（index.html）
- ✅ 使用统计（usage.html）
- ✅ 书签管理（bookmarks.html）
- ✅ 快速面板（popover.html）

**新增功能：**
- 🆕 工具导航中心（tools.html）
- 🆕 最佳实践库（practices.html）

---

## 二、具体实现任务

### 任务 1：优化核心模块导入，实现懒加载

**目标：** 减少启动时的内存占用，将重量级模块改为按需导入

**当前问题：**
```python
# aigard/api/routes.py (第 54-63 行)
# 这些模块在 create_app() 时就被导入，即使用户不使用这些功能
from aigard.api.whitelist import router as whitelist_router
from aigard.api.bookmarks import router as bookmarks_router
from aigard.api.usage import router as usage_router
```

**优化方案：**
```python
def create_app(base_dir: Path, threads_manager) -> FastAPI:
    app = FastAPI(title="AI Guard", version="1.0.0")
    
    # 懒加载：只在首次访问相关 API 时才导入模块
    @app.on_event("startup")
    def lazy_load_routes():
        # 白名单路由（轻量级，可以立即加载）
        from aigard.api.whitelist import router as whitelist_router
        app.include_router(whitelist_router)
    
    # 书签和使用统计路由改为按需加载
    _bookmarks_loaded = False
    _usage_loaded = False
    
    @app.middleware("http")
    async def lazy_load_middleware(request, call_next):
        nonlocal _bookmarks_loaded, _usage_loaded
        
        # 如果访问书签相关 API，才加载书签模块
        if not _bookmarks_loaded and request.url.path.startswith("/api/bookmarks"):
            from aigard.api.bookmarks import router as bookmarks_router
            app.include_router(bookmarks_router)
            _bookmarks_loaded = True
        
        # 如果访问使用统计 API，才加载使用统计模块
        if not _usage_loaded and request.url.path.startswith("/api/usage"):
            from aigard.api.usage import router as usage_router
            app.include_router(usage_router)
            _usage_loaded = True
        
        return await call_next(request)
```

**预期效果：**
- 启动时内存占用减少 20-30MB
- 首次访问书签/使用统计时会有 1-2 秒延迟（可接受）

---

### 任务 2：优化菜单栏刷新频率和数据获取

**目标：** 减少 CPU 占用和不必要的 API 调用

**当前问题：**
```python
# app_menubar.py (第 128 行)
self._timer = rumps.Timer(self._refresh_status, 5)  # 已经是 5 秒

# app_menubar.py (第 249 行)
usage = _main_mod.threads.get_today_usage()  # 每 5 秒调用一次，可能很慢
```

**优化方案：**

1. **缓存今日使用统计**（在 `BackgroundThreads` 中）
```python
# aigard/core/threads.py
class BackgroundThreads:
    def __init__(self, ...):
        self._today_usage_cache = None
        self._today_usage_cache_time = 0
        self._today_usage_cache_ttl = 300  # 5 分钟缓存
    
    def get_today_usage(self):
        """获取今日使用统计（带缓存）"""
        now = time.time()
        if (self._today_usage_cache is not None and 
            now - self._today_usage_cache_time < self._today_usage_cache_ttl):
            return self._today_usage_cache
        
        # 重新计算
        try:
            from aigard.core.usage import ClaudeDataLoader, UsageAggregator
            loader = ClaudeDataLoader()
            entries = loader.load_today()
            agg = UsageAggregator()
            result = agg.aggregate_daily([entries])[0] if entries else {}
            
            self._today_usage_cache = result
            self._today_usage_cache_time = now
            return result
        except Exception as e:
            return {}
```

2. **菜单栏只显示缓存数据**
```python
# app_menubar.py
def _refresh_status(self, _):
    # ... 现有代码 ...
    
    # 使用缓存的今日统计（不会阻塞）
    usage = _main_mod.threads.get_today_usage()
    # ... 现有代码 ...
```

**预期效果：**
- 菜单栏刷新时 CPU 占用从 5-10% 降低到 < 1%
- 首次启动后 5 分钟内，今日统计只计算一次

---

### 任务 3：新增工具导航页面（tools.html）

**目标：** 提供 AI 开发工具的下载链接、教程、配置指南

**页面结构：**
```
🛠️ AI 工具导航
├── Claude Code
│   ├── 官网下载
│   ├── GitHub 仓库
│   ├── 快速上手教程
│   └── 常见问题
├── Cursor
│   ├── 官网下载
│   ├── 配置指南
│   └── 与 Claude 对比
├── GitHub Copilot
├── Windsurf
└── 其他工具...
```

**数据存储：**
```json
// aigard/data/tools.json
{
  "tools": [
    {
      "id": "claude-code",
      "name": "Claude Code",
      "icon": "🤖",
      "description": "Anthropic 官方 AI 编程助手",
      "links": {
        "website": "https://claude.ai/code",
        "github": "https://github.com/anthropics/claude-code",
        "docs": "https://docs.anthropic.com/claude-code"
      },
      "tutorials": [
        {
          "title": "快速上手",
          "url": "https://docs.anthropic.com/claude-code/quickstart"
        }
      ],
      "faqs": [
        {
          "question": "如何安装？",
          "answer": "访问官网下载 macOS 版本..."
        }
      ]
    }
  ]
}
```

**实现文件：**
- `aigard/ui/tools.html` — 前端页面
- `aigard/data/tools.json` — 工具数据
- `aigard/api/routes.py` — 添加 `/tools.html` 路由

---

### 任务 4：新增最佳实践库页面（practices.html）

**目标：** 提供 AI 编程的最佳实践、Prompt 模板、工作流优化建议

**页面结构：**
```
💡 AI 编程最佳实践
├── Prompt 工程
│   ├── 如何写好需求描述
│   ├── 如何让 AI 理解复杂逻辑
│   └── 常见错误示例
├── 工作流优化
│   ├── 如何拆分大任务
│   ├── 如何 Review AI 生成的代码
│   └── 如何处理 AI 的错误
├── 成本优化
│   ├── 如何减少 Token 消耗
│   ├── 如何选择合适的模型
│   └── 缓存策略
└── 安全与隐私
    ├── 如何保护敏感数据
    └── 如何避免代码泄露
```

**数据存储：**
```json
// aigard/data/practices.json
{
  "categories": [
    {
      "id": "prompt-engineering",
      "name": "Prompt 工程",
      "icon": "✍️",
      "practices": [
        {
          "title": "如何写好需求描述",
          "content": "1. 明确目标...\n2. 提供上下文...",
          "examples": [
            {
              "bad": "帮我写个登录功能",
              "good": "实现一个 JWT 登录功能，包含..."
            }
          ]
        }
      ]
    }
  ]
}
```

**实现文件：**
- `aigard/ui/practices.html` — 前端页面
- `aigard/data/practices.json` — 最佳实践数据
- `aigard/api/routes.py` — 添加 `/practices.html` 路由

---

### 任务 5：更新菜单栏添加新功能入口

**目标：** 在菜单栏添加"工具导航"和"最佳实践"入口

**修改文件：** `app_menubar.py`

**新增菜单项：**
```python
self.menu = [
    rumps.MenuItem("📊 快速面板", callback=self._show_popover),
    rumps.separator,
    rumps.MenuItem("打开监控面板", callback=self._open_panel),
    rumps.MenuItem("Claude 使用统计", callback=self._open_usage),
    rumps.MenuItem("🛠️ AI 工具导航", callback=self._open_tools),      # 新增
    rumps.MenuItem("💡 最佳实践", callback=self._open_practices),      # 新增
    rumps.separator,
    # ... 其他菜单项 ...
]

def _open_tools(self, _):
    """打开工具导航"""
    webbrowser.open(f"{self._url}/tools.html")

def _open_practices(self, _):
    """打开最佳实践"""
    webbrowser.open(f"{self._url}/practices.html")
```

---

## 三、设计系统统一

所有新增页面必须遵循现有设计系统：

**参考：** `aigard/ui/css/design-system.css`

**核心规范：**
- 暗色主题：`#0d1117` 背景、`#58a6ff` 强调色、`#30363d` 边框
- 亮色主题：`#ffffff` 背景、`#0969da` 强调色、`#d0d7de` 边框
- 字体：`-apple-system, 'Segoe UI', 'Noto Sans'`
- 圆角：`12px` 卡片、`8px` 按钮
- 无 Emoji 图标，使用 SVG 或 Unicode 符号

---

## 四、实施顺序

1. ✅ **任务 2**：优化菜单栏（最小改动，立即见效）
2. ✅ **任务 1**：优化模块导入（核心优化，减少内存）
3. ✅ **任务 3**：新增工具导航（快速验证新方向）
4. ✅ **任务 4**：新增最佳实践（内容密集，需要时间）
5. ✅ **任务 5**：更新菜单栏（最后集成）

---

## 五、验证标准

### 5.1 性能指标

**启动时内存占用：**
- 优化前：~80MB
- 优化后：< 50MB（减少 30MB+）

**菜单栏刷新 CPU 占用：**
- 优化前：5-10%
- 优化后：< 1%

**首次访问延迟：**
- 书签管理：< 2 秒
- 使用统计：< 2 秒
- 工具导航：< 0.5 秒（静态内容）
- 最佳实践：< 0.5 秒（静态内容）

### 5.2 功能验证

**必须测试：**
1. 启动应用后，不打开任何页面，内存占用 < 50MB
2. 打开监控面板，内存增加 < 20MB
3. 打开使用统计，首次加载 < 2 秒
4. 菜单栏刷新时，CPU 占用 < 1%
5. 工具导航和最佳实践页面正常显示

---

## 六、后续扩展（v2.0）

如果用户反馈良好，可以考虑：

1. **社区贡献**
   - 允许用户提交工具推荐
   - 允许用户分享最佳实践
   - GitHub Discussions 或 Wiki

2. **智能推荐**
   - 根据项目类型推荐工具
   - 根据使用习惯推荐最佳实践

3. **AI 使用分析报告**
   - 不仅显示费用，还分析效率
   - 对比传统开发的时间节省
   - 优化建议（如使用更便宜的模型）

4. **插件系统**
   - 允许第三方开发者扩展功能
   - 提供 API 和 SDK

---

## 七、风险与注意事项

### 7.1 懒加载的风险

**问题：** FastAPI 的 `include_router()` 不能在运行时动态调用

**解决方案：** 使用中间件拦截请求，在首次访问时加载模块

**备选方案：** 如果中间件方案不可行，改为在 `startup` 事件中加载所有路由，但使用懒加载的数据加载器

### 7.2 内容维护成本

**问题：** 工具导航和最佳实践需要持续更新

**解决方案：**
- 使用 JSON 文件存储数据，易于编辑
- 提供 GitHub PR 模板，方便社区贡献
- 定期（每月）检查链接有效性

### 7.3 用户体验

**问题：** 首次访问重量级功能时会有延迟

**解决方案：**
- 显示加载动画（"正在加载..."）
- 缓存加载结果，后续访问无延迟
- 在菜单栏添加"预加载"选项（可选）

---

## 八、成功标准

**短期（v1.2）：**
- ✅ 启动内存 < 50MB
- ✅ 菜单栏 CPU < 1%
- ✅ 工具导航和最佳实践页面上线
- ✅ 用户反馈积极（GitHub Issues/Discussions）

**长期（v2.0）：**
- ✅ 社区贡献 > 10 个工具/实践
- ✅ 月活用户 > 1000
- ✅ GitHub Stars > 500
- ✅ 付费支持 > $100/月

---

**计划创建时间：** 2026-05-27  
**预计完成时间：** 2026-05-28  
**负责人：** Xaiver03
