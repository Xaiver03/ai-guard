# AI Guard UI 统一计划 - 三 Agent 并行任务分配

## 背景

AI Guard 项目需要将所有 Web UI 页面的设计风格统一为 ccusage 的 GitHub Dark 主题。
ccusage 的原版 UI (React) 需要被 1:1 复刻为 Vanilla JS。
所有页面需要支持 i18n（中英文切换）和暗色/亮色双主题。

## 关键文件位置

- 项目根目录：`/Users/rocalight/Desktop/All in one Data/01_PROJECTS/AI Guard`
- ccusage 原版参考：`/Users/rocalight/Desktop/All in one Data/01_PROJECTS/ccusage`
- AI Guard 前端目录：`aigard/ui/`
- API 路由：`aigard/api/`
- 后端核心：`aigard/core/`

## ccusage 原版 UI 参考文件

**必须阅读这些文件来理解原版 UI：**
- `/Users/rocalight/Desktop/All in one Data/01_PROJECTS/ccusage/apps/web/src/App.jsx` - 主组件（1317行）
- `/Users/rocalight/Desktop/All in one Data/01_PROJECTS/ccusage/apps/web/src/App.css` - 样式（817行）
- `/Users/rocalight/Desktop/All in one Data/01_PROJECTS/ccusage/apps/web/src/PricingConfig.jsx` - 定价配置组件
- `/Users/rocalight/Desktop/All in one Data/01_PROJECTS/ccusage/apps/web/src/Icons.jsx` - SVG 图标组件
- `/Users/rocalight/Desktop/All in one Data/01_PROJECTS/ccusage/apps/web/src/index.css` - 全局样式

## 设计规范（严格遵守）

### 配色

**暗色主题（默认）：**
```css
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
```

**亮色主题：**
```css
--bg-primary: #f6f8fa;
--bg-secondary: #ffffff;
--bg-card: #ffffff;
--text-primary: #1f2328;
--text-secondary: #656d76;
--accent-blue: #0969da;
--accent-green: #1a7f37;
--accent-orange: #9a6700;
--accent-red: #cf222e;
--accent-purple: #8250df;
--border-color: #d0d7de;
```

### 通用规则

1. **不使用任何 Emoji** - 全部使用 SVG 图标
2. **所有页面撑满整个浏览器窗口** - 自适应布局
3. **三个导航 Tab 在所有页面一致显示**：监控面板 / Claude 统计 / 书签管理
4. **所有文本支持 i18n 中英文切换**
5. **字体**：-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif
6. **等宽字体**：'SF Mono', 'Fira Code', Consolas, monospace
7. **卡片圆角**：12px / **按钮圆角**：8px / **输入框圆角**：6px

### API 端点

**系统监控：**
- `GET /api/metrics` - 当前系统指标
- `GET /api/stream` - SSE 实时推流
- `GET /api/processes` - AI 进程列表
- `GET /api/processes/all` - 所有进程列表

**Claude 使用统计：**
- `GET /api/usage/summary?preset=today` - 统计总览
- `GET /api/usage/daily?preset=this_month` - 每日统计
- `GET /api/usage/hourly?preset=today` - 每小时统计
- `GET /api/usage/models?preset=this_month` - 模型统计
- `GET /api/usage/pricing` - 获取定价配置
- `POST /api/usage/pricing` - 更新定价配置
- `POST /api/usage/refresh` - 刷新数据

**书签：**
- `GET /api/bookmarks` - 书签列表
- `POST /api/bookmarks/analyze` - AI 分析

---

## Agent 1 任务：1:1 复刻 ccusage 的 Claude 统计页面

**文件：`aigard/ui/usage.html`**

**目标：** 将 ccusage 的 React Dashboard 完整用 Vanilla JS 复刻，不能有任何功能缺失或样式差异。

**必须实现的功能（参考 App.jsx）：**

1. **Header 区域**
   - 标题 "Claude Code 综合面板" + 副标题
   - 导航标签（数据面板 / 定价配置）
   - 中英文切换按钮
   - 数字格式切换（紧凑 1.2M / 完整 1,234,567）
   - 刷新按钮（带旋转动画 + 状态消息）
   - 数据生成时间显示

2. **时间范围选择器**
   - 今日、昨天、近三天、本周、本月、全部
   - 自定义日期范围（日期选择器）

3. **统计卡片（4 + 5 个）**
   - 总 Token 数（带分类/总计切换）
   - 总费用（带"估算"标记）
   - 活跃天数
   - 使用模型数
   - 输入 Token / 输出 Token / 缓存写入 / 缓存读取 / 总请求数

4. **图表区域（2 列布局）**
   - Token 使用趋势（折线图/柱状图，按时间范围切换）
   - 费用趋势（折线图/柱状图）

5. **底部区域**
   - 模型使用分布（饼图 + 图例）
   - 模型使用详细统计表格

6. **最近使用记录表格**

7. **定价配置页面（PricingConfig）**
   - 模型定价表（可编辑）
   - 添加自定义模型
   - 重置定价

8. **i18n 支持**
   - 所有文本通过 translations 对象管理
   - 中英文一键切换

**CSS 规则：** 完全复制 ccusage 的 App.css（817 行），修改为 CSS 变量以支持双主题

**注意：**
- 数据来自 `/api/usage/*` 端点
- 必须支持暗色/亮色双主题（localStorage 持久化）
- 图表使用 Chart.js CDN
- 三个顶部导航 Tab 必须一致

---

## Agent 2 任务：重写监控面板页面

**文件：`aigard/ui/index.html`**

**目标：** 将现有的监控面板 UI 改为与 ccusage 完全一致的设计风格，同时保留所有现有功能。

**需要保持的功能（不能删除或改变行为）：**

1. **资源压力仪表**
   - 内存、Swap、磁盘、CPU 进度条
   - 详细信息（已用/总量）

2. **趋势图（2 列）**
   - 内存 & Swap 趋势
   - CPU & 磁盘趋势

3. **进程表**
   - AI/开发进程 和 所有进程 视图切换
   - 批量操作栏
   - 进程表格（PID、进程名、命令行、内存、CPU、状态、安全评估、操作）

4. **自动终止日志**

5. **启动拦截黑名单**

6. **设置抽屉**

7. **SSE 实时推流**

**需要修改的：**

1. **CSS 变量统一** - 使用 ccusage 的 GitHub Dark 配色
2. **亮色主题** - 添加完整的亮色主题支持
3. **移除所有 Emoji** - 替换为 SVG 图标
4. **三个导航 Tab** - 统一显示（监控面板/Claude 统计/书签管理）
5. **i18n** - 所有文本支持中英文切换
6. **全屏自适应** - 内容撑满浏览器窗口
7. **统一组件样式** - 卡片、按钮、表格、输入框等与 ccusage 一致

**CSS 转换参考：**

| 旧变量 | 新变量（暗色） |
|--------|---------------|
| `--bg: #0f1117` | `--bg: #0d1117` |
| `--card: #1a1d27` | `--card: #161b22` |
| `--border: #2a2d3e` | `--border: #30363d` |
| `--blue: #3b82f6` | `--blue: #58a6ff` |
| `--green: #22c55e` | `--green: #3fb950` |

---

## Agent 3 任务：重写书签管理页面

**文件：`aigard/ui/bookmarks.html`**

**目标：** 将书签管理页面重写为与 ccusage 一致的设计风格，丰富功能和界面。

**当前问题：**
- 界面过于简单
- 全部是英文，没有中英文切换
- 导航 Tab 不一致（有时只显示 2 个）
- 风格与其他页面不统一

**需要实现的功能：**

1. **统一 Header** - 与其他页面完全一致的三个导航 Tab
2. **i18n** - 所有文本支持中英文切换
3. **统一配色和组件样式** - ccusage GitHub Dark 主题
4. **丰富界面**：
   - 书签总数统计卡片
   - 分类统计（按文件夹分组）
   - 搜索/筛选功能
   - 书签列表（表格或卡片视图）
   - AI 分析结果展示区域
5. **亮色/暗色双主题**
6. **全屏自适应布局**

**API 端点：**
- `GET /api/bookmarks` - 获取书签列表
- `POST /api/bookmarks/analyze` - AI 分析

**参考现有的 bookmarks.html 了解当前结构和 API 调用方式。**

---

## 共享约定

### 导航栏 HTML（所有页面必须一致）

```html
<header class="header">
  <div class="header-left">
    <h1 class="logo">AI <span>Guard</span></h1>
  </div>
  <div class="header-right">
    <div class="nav-tabs">
      <a href="/" class="nav-tab {active if current}">监控面板</a>
      <a href="/usage.html" class="nav-tab {active if current}">Claude 统计</a>
      <a href="/bookmarks.html" class="nav-tab {active if current}">书签管理</a>
    </div>
    <div class="format-toggle">
      <button class="{active if zh}" onclick="setLang('zh')">中</button>
      <button class="{active if en}" onclick="setLang('en')">EN</button>
    </div>
    <button class="icon-btn" onclick="toggleTheme()" title="切换主题">
      <!-- SVG moon/sun icon -->
    </button>
  </div>
</header>
```

### i18n 模式

```javascript
const translations = {
  zh: { /* 中文翻译 */ },
  en: { /* 英文翻译 */ }
};
let _lang = localStorage.getItem('ai-guard-lang') || 'zh';
const t = () => translations[_lang];

function setLang(lang) {
  _lang = lang;
  localStorage.setItem('ai-guard-lang', lang);
  updateAllText();
}
```

### 主题切换

```javascript
function toggleTheme() {
  const cur = document.documentElement.getAttribute('data-theme') || 'dark';
  const next = cur === 'dark' ? 'light' : 'dark';
  localStorage.setItem('ai-guard-theme', next);
  document.documentElement.setAttribute('data-theme', next);
  // 更新图表颜色等
}
```

---

## 验收标准

1. 三个页面的导航栏、配色、组件样式完全一致
2. ccusage 统计页面与原版 1:1 一致（功能和外观）
3. 所有文本支持中英文切换
4. 暗色/亮色双主题正常工作
5. 无任何 Emoji
6. 所有页面撑满浏览器窗口
7. 响应式布局正常（移动端/桌面端）
