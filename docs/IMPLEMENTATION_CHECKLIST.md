# AI Guard + ccusage 深度融合实施清单

## 项目概述

将 ccusage（TypeScript/React）完全重写并深度融合到 AI Guard（Python/Vanilla JS）中。

**技术栈转换：**
- TypeScript → Python 3.11
- React 19 → Vanilla JavaScript
- Vite → 无构建工具（直接加载）
- pnpm workspace → Python 模块

**设计系统：**
- 基准：ccusage 的 GitHub Dark 主题
- 配色：#0d1117 (背景), #58a6ff (强调色)
- 字体：-apple-system, Fira Code (代码)
- 移除所有 Emoji，使用纯文本或 SVG 图标

---

## 📋 实施清单

### Phase 1: 后端核心模块（aigard/core/usage/）

#### 1.1 数据模型
- [x] `models.py` - 数据类定义
  - UsageEntry, DailySummary, HourlySummary, MonthlySummary
  - ModelBreakdown

#### 1.2 数据加载器
- [ ] `loader.py` - JSONL 文件解析器
  - 扫描 `~/.claude/projects/` 目录
  - 解析 `{sessionId}.jsonl` 文件
  - 提取 token 使用数据
  - 处理多项目、多会话

#### 1.3 计算器
- [ ] `calculator.py` - Token 和费用计算
  - 计算 input/output/cache tokens
  - 根据模型定价计算费用
  - 支持自定义定价配置

#### 1.4 聚合器
- [ ] `aggregator.py` - 数据聚合逻辑
  - 按小时聚合（HourlySummary）
  - 按日聚合（DailySummary）
  - 按月聚合（MonthlySummary）
  - 按模型聚合（ModelBreakdown）

#### 1.5 定价管理
- [ ] `pricing.py` - 模型定价管理
  - 默认定价表（Claude 4.6, 4.5, 3.5 等）
  - 从配置文件加载自定义定价
  - 定价更新和持久化

#### 1.6 模块入口
- [x] `__init__.py` - 导出所有公共接口

---

### Phase 2: API 路由（aigard/api/）

#### 2.1 Claude 使用统计 API
- [ ] `usage.py` - 新建文件
  - `GET /api/usage/summary` - 总览数据
  - `GET /api/usage/daily` - 日报数据
  - `GET /api/usage/hourly` - 小时报数据
  - `GET /api/usage/monthly` - 月报数据
  - `GET /api/usage/models` - 模型使用统计
  - `GET /api/usage/projects` - 项目列表
  - `GET /api/usage/pricing` - 获取定价配置
  - `POST /api/usage/pricing` - 更新定价配置
  - `POST /api/usage/refresh` - 刷新数据

#### 2.2 集成到主应用
- [ ] `main.py` - 修改
  - 导入 usage 路由
  - 注册到 FastAPI app

---

### Phase 3: 前端设计系统（aigard/ui/css/）

#### 3.1 设计系统变量
- [ ] `design-system.css` - 新建文件
  - CSS 变量定义（颜色、字体、间距、圆角）
  - 基于 ccusage 的 GitHub Dark 主题
  - 移除所有 Emoji 相关样式

#### 3.2 组件样式
- [ ] `components.css` - 新建文件
  - 卡片组件（.card, .metric-card）
  - 按钮组件（.btn, .btn-primary, .btn-secondary）
  - 表格组件（.table, .table-row）
  - 标签页组件（.tabs, .tab-button）
  - 图表容器（.chart-container）
  - 加载状态（.loading, .spinner）

#### 3.3 更新现有样式
- [ ] 修改 `index.html` 中的内联样式
  - 提取到独立 CSS 文件
  - 统一使用设计系统变量
  - 移除所有 Emoji

---

### Phase 4: 前端页面结构（aigard/ui/）

#### 4.1 主页面更新
- [ ] `index.html` - 修改
  - 添加标签页切换结构
    - Tab 1: 系统监控（现有功能）
    - Tab 2: Claude 使用统计（新功能）
  - 引入新的 CSS 文件
  - 引入新的 JS 模块
  - 移除所有 Emoji

#### 4.2 Claude 使用统计页面
- [ ] `usage.html` - 新建文件（或嵌入 index.html）
  - 顶部指标卡片（总 Token、总费用、活跃天数、模型数）
  - 时间范围选择器（今日、昨天、近三天、本周、本月、全部、自定义）
  - 图表区域
    - Token 使用趋势（折线图）
    - 费用趋势（折线图）
    - 模型使用分布（饼图）
    - 小时使用分布（柱状图）
  - 模型详细统计表格
  - 最近使用记录表格

---

### Phase 5: 前端逻辑（aigard/ui/js/）

#### 5.1 核心逻辑模块
- [ ] `usage.js` - 新建文件（~1000 行）
  - 数据获取（fetch API）
  - 状态管理（纯 JS 对象）
  - 时间范围筛选逻辑
  - 数据格式化（数字、日期、货币）
  - 表格渲染
  - 事件监听（按钮点击、筛选器变化）

#### 5.2 图表渲染模块
- [ ] `charts.js` - 新建文件（~500 行）
  - Chart.js 配置
  - 折线图渲染（Token 趋势、费用趋势）
  - 饼图渲染（模型分布）
  - 柱状图渲染（小时分布）
  - 图表主题配置（GitHub Dark）
  - 响应式图表更新

#### 5.3 工具函数模块
- [ ] `utils.js` - 新建文件
  - 数字格式化（1234567 → 1.2M）
  - 日期格式化
  - 货币格式化
  - 时间范围计算
  - 数据聚合辅助函数

#### 5.4 标签页切换逻辑
- [ ] 修改现有 `index.html` 中的 JS
  - 实现标签页切换
  - 保存当前标签页状态
  - 切换时加载对应数据

---

### Phase 6: 菜单栏集成（app_menubar.py）

#### 6.1 添加菜单项
- [ ] `app_menubar.py` - 修改
  - 添加"Claude 使用统计"菜单项
  - 点击时打开 Web UI 并切换到 Claude 统计标签页
  - 添加"刷新 Claude 数据"菜单项

---

### Phase 7: 配置文件更新

#### 7.1 应用配置
- [ ] `config.toml` - 修改
  - 添加 `[usage]` 部分
  - 配置 Claude 数据目录路径
  - 配置默认时间范围
  - 配置定价表

#### 7.2 Python 依赖
- [ ] `requirements.txt` - 修改
  - 确认所有依赖已包含（无需新增）

---

### Phase 8: 打包配置

#### 8.1 打包脚本
- [ ] `setup.py` - 修改
  - 确保 `aigard/core/usage/` 被包含
  - 确保新的 CSS/JS 文件被包含

#### 8.2 构建脚本
- [ ] `build.sh` - 验证
  - 运行构建流程
  - 验证 .app 包含所有新文件

---

### Phase 9: 测试

#### 9.1 单元测试
- [ ] `tests/test_usage_loader.py` - 新建
- [ ] `tests/test_usage_calculator.py` - 新建
- [ ] `tests/test_usage_aggregator.py` - 新建

#### 9.2 集成测试
- [ ] `tests/test_usage_api.py` - 新建
  - 测试所有 API 端点
  - 测试数据格式

#### 9.3 UI 测试
- [ ] 手动测试标签页切换
- [ ] 手动测试图表渲染
- [ ] 手动测试时间范围筛选
- [ ] 手动测试菜单栏集成

---

### Phase 10: 文档

#### 10.1 用户文档
- [ ] `docs/USAGE_GUIDE.md` - 新建
  - Claude 使用统计功能说明
  - 如何查看数据
  - 如何自定义定价

#### 10.2 开发文档
- [ ] `docs/ARCHITECTURE.md` - 更新
  - 添加 usage 模块架构说明

---

## 🎯 关键技术点

### 1. JSONL 解析（loader.py）

ccusage 的数据源是 `~/.claude/projects/{project}/{sessionId}.jsonl`，每行是一个 JSON 对象：

```json
{
  "type": "usage",
  "input_tokens": 1234,
  "output_tokens": 567,
  "cache_creation_input_tokens": 100,
  "cache_read_input_tokens": 50
}
```

需要：
- 递归扫描所有项目目录
- 解析每个 JSONL 文件
- 提取 usage 类型的记录
- 关联到项目和会话

### 2. Token 计算（calculator.py）

根据 ccusage 的逻辑：
- `total_tokens = input_tokens + output_tokens + cache_creation_tokens + cache_read_tokens`
- `cost = (input_tokens * input_price) + (output_tokens * output_price) + (cache_creation * cache_creation_price) + (cache_read * cache_read_price)`

### 3. 数据聚合（aggregator.py）

需要支持：
- 按小时聚合：`2026-05-24T14` → 该小时的所有数据
- 按日聚合：`2026-05-24` → 该天的所有数据
- 按月聚合：`2026-05` → 该月的所有数据
- 按模型聚合：每个模型的独立统计

### 4. 前端数据流（usage.js）

```
用户选择时间范围
  ↓
fetch /api/usage/daily?start=xxx&end=xxx
  ↓
解析 JSON 数据
  ↓
更新指标卡片
  ↓
更新图表（charts.js）
  ↓
更新表格
```

### 5. 图表配置（charts.js）

使用 Chart.js，配置 GitHub Dark 主题：
- 背景色：透明
- 网格线：#30363d
- 文本颜色：#8b949e
- 数据线颜色：#58a6ff, #3fb950, #d29922, #f85149

---

## 📊 工作量评估

| 阶段 | 文件数 | 预计代码行数 | 预计时间 |
|------|--------|--------------|----------|
| Phase 1: 后端核心 | 5 | ~800 | 2-3 小时 |
| Phase 2: API 路由 | 2 | ~300 | 1 小时 |
| Phase 3: 设计系统 | 2 | ~400 | 1 小时 |
| Phase 4: 页面结构 | 1 | ~200 | 1 小时 |
| Phase 5: 前端逻辑 | 3 | ~1500 | 3-4 小时 |
| Phase 6: 菜单栏 | 1 | ~50 | 0.5 小时 |
| Phase 7: 配置 | 2 | ~50 | 0.5 小时 |
| Phase 8: 打包 | 2 | ~50 | 0.5 小时 |
| Phase 9: 测试 | 4 | ~400 | 2 小时 |
| Phase 10: 文档 | 2 | ~300 | 1 小时 |
| **总计** | **24** | **~4050** | **12-15 小时** |

---

## 🚀 下一步行动

现在有两个选择：

### 选项 A：我立即开始完整实施
- 我会按照上述清单逐个完成所有文件
- 预计需要持续工作几个小时
- 你可以随时查看进度或中断

### 选项 B：你先审查清单，然后决定
- 你可以调整优先级
- 你可以选择只实施某些部分
- 你可以提出修改建议

**你希望我现在立即开始完整实施吗？**
