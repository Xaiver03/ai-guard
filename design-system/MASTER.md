# AI Guard — 设计系统 MASTER

> **Source of Truth** · 由 UI/UX Pro Max 生成 · 2026-05-24  
> 所有页面（index、usage、bookmarks）均遵守此文件。如需页面级覆盖，在 `design-system/pages/<page>.md` 中声明。

---

## 1. 产品定位

| 维度 | 定义 |
|------|------|
| **产品类型** | Developer Tool / Real-Time Operations Dashboard |
| **目标用户** | AI 开发者、使用 Claude Code/Codex/Cursor 的专业工程师 |
| **使用场景** | 长时间开发中监控资源压力、干预进程、查看 Token 消耗 |
| **风格关键词** | Precision · Dark · Minimal · Data-Dense · Professional |
| **参考设计** | GitHub Dark + 系统监控仪表盘（Grafana / htop 美学） |

---

## 2. 设计风格

**选定风格：Dark Mode (OLED) — 开发者工具变体**

参考 UI Pro Max 推荐：`Dark Mode (OLED)` + `Developer Tool` 产品类型

| 属性 | 规范 |
|------|------|
| 主要模式 | 暗色主题（默认），亮色主题（辅助） |
| 视觉密度 | 数据密集但可扫描（data-dense but scannable） |
| 图标风格 | SVG 线条图标（stroke-width: 1.5px），**禁止使用 Emoji** |
| 效果 | 极简 glow（仅用于强调状态），无装饰性动效 |
| 圆角哲学 | 功能性圆角：卡片 12px，按钮 8px，输入框 6px，徽章 999px |

---

## 3. 颜色系统

### 3.1 暗色主题（默认）

基于 GitHub Dark 配色，由 UI Pro Max Developer Tool 调色板验证：

```css
/* 背景层级（4 层，从深到浅） */
--bg-primary:    #0d1117;   /* 页面底色 */
--bg-secondary:  #161b22;   /* 卡片背景 */
--bg-tertiary:   #1c2128;   /* 卡片内嵌区 / hover 基底 */
--bg-elevated:   #21262d;   /* 浮层、下拉、抽屉 */

/* 文本层级（4 层） */
--text-primary:   #e6edf3;  /* 主要内容 ≥4.5:1 */
--text-secondary: #8b949e;  /* 次要标签 ≥3:1 */
--text-tertiary:  #6e7681;  /* 辅助信息 */
--text-disabled:  #484f58;  /* 禁用状态 */

/* 语义强调色 */
--accent-blue:   #58a6ff;   /* 主操作、链接、focus */
--accent-green:  #3fb950;   /* 成功、安全、运行 */
--accent-yellow: #d29922;   /* 警告、谨慎 */
--accent-red:    #f85149;   /* 危险、错误、终止 */
--accent-purple: #bc8cff;   /* Swap、缓存、紫色标记 */
--accent-orange: #e3b341;   /* 次级警告 */

/* 边框 */
--border-default: #30363d;
--border-subtle:  #21262d;
--border-focus:   #58a6ff;

/* 状态色别名（和语义色对应） */
--status-ok:      var(--accent-green);
--status-warn:    var(--accent-yellow);
--status-crit:    var(--accent-red);
--status-info:    var(--accent-blue);

/* 透明度 */
--overlay-scrim:  rgba(0, 0, 0, 0.5);

/* 图表颜色（可访问，非纯红/绿依赖） */
--chart-memory:  #58a6ff;   /* 蓝 */
--chart-swap:    #bc8cff;   /* 紫 */
--chart-cpu:     #3fb950;   /* 绿 */
--chart-disk:    #d29922;   /* 黄 */
```

### 3.2 亮色主题

```css
--bg-primary:    #f6f8fa;
--bg-secondary:  #ffffff;
--bg-tertiary:   #f6f8fa;
--bg-elevated:   #eaeef2;

--text-primary:   #1f2328;
--text-secondary: #656d76;
--text-tertiary:  #8b949e;
--text-disabled:  #c9d1d9;

--accent-blue:   #0969da;
--accent-green:  #1a7f37;
--accent-yellow: #9a6700;
--accent-red:    #cf222e;
--accent-purple: #8250df;
--accent-orange: #bc4c00;

--border-default: #d0d7de;
--border-subtle:  #eaeef2;
--border-focus:   #0969da;

--chart-memory:  #0969da;
--chart-swap:    #8250df;
--chart-cpu:     #1a7f37;
--chart-disk:    #9a6700;
```

### 3.3 颜色使用规则

1. **不得直接在组件中硬编码 hex** — 必须使用 CSS 变量
2. **对比度要求**：主要文本 ≥4.5:1，次要文本 ≥3:1（WCAG AA）
3. **颜色不是唯一语义载体** — 错误/成功状态必须同时包含图标或文字
4. 进度条颜色动态切换（≥90% 红，≥70% 黄，其余绿）
5. 透明度变体使用语义色 + alpha，如 `rgba(63,185,80,.12)` 不要用 `rgba(green)`

---

## 4. 排版系统

**选定字体：Inter（UI 文本）+ SF Mono/JetBrains Mono（等宽数据）**

```css
--font-sans: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans',
             Helvetica, Arial, sans-serif;
--font-mono: 'SF Mono', 'JetBrains Mono', 'Fira Code',
             'Consolas', 'Monaco', monospace;
```

### 字体比例

| Token | rem | px | 用途 |
|-------|-----|----|------|
| `--text-2xs` | 0.6875rem | 11px | 标签大写、表头 |
| `--text-xs`  | 0.75rem   | 12px | 辅助信息、时间戳 |
| `--text-sm`  | 0.875rem  | 14px | 表格内容、按钮 |
| `--text-base`| 1rem      | 16px | 正文（最小移动端字体） |
| `--text-lg`  | 1.125rem  | 18px | 卡片标题 |
| `--text-xl`  | 1.25rem   | 20px | 页面小标题 |
| `--text-2xl` | 1.5rem    | 24px | 统计数值 |
| `--text-3xl` | 1.875rem  | 30px | 主要指标数值 |

### 字重

| Token | 值 | 用途 |
|-------|-----|------|
| `--weight-normal`   | 400 | 正文 |
| `--weight-medium`   | 500 | 标签、按钮 |
| `--weight-semibold` | 600 | 标题、重要数据 |
| `--weight-bold`     | 700 | 主要数值、Logo |

### 行高

- 正文内容：`line-height: 1.5`
- 标题 / 数值：`line-height: 1.2`
- 表格行：`line-height: 1.4`
- **数值列必须使用等宽数字**：`font-variant-numeric: tabular-nums`

---

## 5. 间距系统

基于 **4px 基准网格**（8dp rhythm）：

```css
--space-1:  0.25rem;  /*  4px */
--space-2:  0.5rem;   /*  8px */
--space-3:  0.75rem;  /* 12px */
--space-4:  1rem;     /* 16px */
--space-5:  1.25rem;  /* 20px */
--space-6:  1.5rem;   /* 24px */
--space-8:  2rem;     /* 32px */
--space-10: 2.5rem;   /* 40px */
--space-12: 3rem;     /* 48px */
--space-16: 4rem;     /* 64px */
```

### 间距语义

| 场景 | Token |
|------|-------|
| 图标与文字间距 | `--space-1` (4px) |
| 行内元素间距 | `--space-2` (8px) |
| 组件内部 padding | `--space-3` ~ `--space-4` |
| 卡片 padding | `--space-4` ~ `--space-5` |
| 卡片间距（grid gap） | `--space-4` |
| 卡片标题与内容 | `--space-3` |
| 页面主内容区 padding | `--space-5` (20px) 上下，`--space-6` (24px) 左右 |

---

## 6. 圆角系统

```css
--radius-xs:   4px;    /* 极小元素 */
--radius-sm:   6px;    /* 输入框、小按钮 */
--radius-md:   8px;    /* 常规按钮 */
--radius-lg:   10px;   /* 浮层、抽屉 */
--radius-xl:   12px;   /* 卡片 */
--radius-full: 9999px; /* 徽章、胶囊按钮、进度条 */
```

---

## 7. 阴影系统

```css
--shadow-sm:    0 1px 2px rgba(0,0,0,.2);
--shadow-card:  0 1px 3px rgba(0,0,0,.2), 0 1px 2px rgba(0,0,0,.12);
--shadow-hover: 0 4px 12px rgba(0,0,0,.3);
--shadow-modal: 0 8px 24px rgba(0,0,0,.4), 0 2px 8px rgba(0,0,0,.2);
--shadow-focus: 0 0 0 3px rgba(88,166,255,.2);
```

亮色主题对应值：
```css
--shadow-card:  0 1px 3px rgba(31,35,40,.12), 0 8px 24px rgba(66,74,83,.12);
--shadow-hover: 0 4px 12px rgba(31,35,40,.2);
--shadow-modal: 0 8px 32px rgba(31,35,40,.24);
--shadow-focus: 0 0 0 3px rgba(9,105,218,.2);
```

---

## 8. 动效系统

> 规则：duration 150–300ms，transform/opacity only，不动 width/height/top/left

```css
--ease-out:    cubic-bezier(0.0, 0.0, 0.2, 1);   /* 进入 */
--ease-in:     cubic-bezier(0.4, 0.0, 1, 1);      /* 退出 */
--ease-inout:  cubic-bezier(0.4, 0.0, 0.2, 1);    /* 内部转场 */
--ease-spring: cubic-bezier(0.16, 1, 0.3, 1);     /* 弹性反馈（按钮/卡片） */

--duration-fast:   150ms;   /* 微交互：hover、icon 变色 */
--duration-base:   200ms;   /* 标准：按钮、输入框 */
--duration-slow:   300ms;   /* 页面内切换、抽屉 */
--duration-slower: 400ms;   /* 加载动画 */
```

### 动效规则

1. **进入用 ease-out，退出用 ease-in**
2. **退出动画时长 = 进入的 60%**（感觉更响应）
3. **只动 transform 和 opacity**，避免 reflow
4. **按钮按压反馈**：`scale(0.97)` → `scale(1.0)`，duration 150ms
5. **悬停状态**：150ms，不加 delay
6. **模态框/抽屉**：translateX/Y + opacity，300ms ease-out 进入
7. **骨架屏闪烁**：shimmer 用 `background-position` 动画（非 opacity）
8. **尊重 `prefers-reduced-motion`**：检测到减少动效首选项时，只保留 opacity 切换

---

## 9. 布局系统

### Header（固定顶部）

```
高度: 57px（紧凑）
左: Logo "AI Guard"
中: 三个导航 Tab（居中）
右: 语言切换 | 主题切换 | 功能按钮 | 状态徽章
内边距: 0 24px
边框: border-bottom 1px --border-default
```

### 导航 Tab 规范

```
容器: background --bg-tertiary, border 1px --border-default, border-radius 8px, padding 3px
单个 Tab: padding 5px 14px, border-radius 6px
激活态: background --bg-secondary, color --text-primary, font-weight 600
非激活: color --text-secondary, hover → color --text-primary + background --bg-tertiary
```

**导航顺序（所有页面一致）：**
1. 监控面板 → `/`
2. Claude 统计 → `/usage.html`
3. 书签管理 → `/bookmarks.html`

### 主内容区

```
padding: 20px 24px
display: grid
gap: 16px
max-width: 无（撑满浏览器）
```

### 响应式断点

| 断点 | 宽度 | 策略 |
|------|------|------|
| Mobile | < 640px | 单列，隐藏次要列 |
| Tablet | 640–1024px | 2 列布局 |
| Desktop | 1024–1440px | 完整 2 列 |
| Wide | ≥ 1440px | 同 Desktop，内容不超过合理宽度 |

---

## 10. 组件规范

### 卡片（Card）

```
background: --bg-secondary
border: 1px solid --border-default
border-radius: --radius-xl (12px)
padding: --space-4 --space-5 (16px 20px)
transition: background 200ms, border-color 200ms
```

### 按钮（Button）

```
padding: 5px 12px
border-radius: --radius-md (8px)
font-size: --text-sm (14px)
font-weight: --weight-semibold (600)
transition: opacity 150ms
cursor: pointer

:hover → opacity 0.8
:active → transform: scale(0.97)
:disabled → opacity 0.35, cursor: not-allowed

变体:
.btn-primary  → bg rgba(63,185,80,.12)  color --accent-green
.btn-warning  → bg rgba(210,153,34,.12) color --accent-yellow
.btn-danger   → bg rgba(248,81,73,.12)  color --accent-red
.btn-muted    → bg --bg-elevated        color --text-secondary
.btn-blue     → bg rgba(88,166,255,.15) color --accent-blue

小型 .btn-sm:
padding: 3px 8px
border-radius: --radius-sm (6px)
font-size: 11px
```

### 状态徽章（Status Badge）

```
padding: 4px 12px
border-radius: --radius-full
font-size: 12px, font-weight: 600
display: inline-flex, align-items: center, gap: 5px

ok   → bg rgba(63,185,80,.12)   color --accent-green
warn → bg rgba(210,153,34,.12)  color --accent-yellow  
crit → bg rgba(248,81,73,.12)   color --accent-red + animation: pulse 1s
```

### 图标按钮（Icon Button）

```
width: 32px, height: 32px
border-radius: --radius-md (8px)
border: 1px solid --border-default
background: transparent
color: --text-secondary
cursor: pointer
transition: background 150ms, color 150ms

:hover → background --bg-tertiary, color --text-primary
```

### 进度条（Gauge Bar）

```
容器高度: 8px, border-radius: --radius-full, background: --bg-elevated
填充: border-radius: --radius-full, transition: width 300ms ease, background 300ms

颜色逻辑:
pct >= 90 → --accent-red
pct >= 70 → --accent-yellow
pct <  70 → --accent-green
```

### 表格（Table）

```
表头: font-size 11px, uppercase, letter-spacing .5px, color --text-secondary
      padding: 6px 8px, border-bottom: 1px solid --border-default
单元格: padding 7px 8px, font-size 13px, border-bottom: 1px --border-default
行 hover: background --bg-tertiary
数值列: font-variant-numeric: tabular-nums
```

### 输入框（Input）

```
background: --bg-primary
border: 1px solid --border-default
border-radius: --radius-sm (6px)
padding: 5px 8px
color: --text-primary
font-size: 13px
transition: border-color 150ms

:focus → border-color: --border-focus, box-shadow: --shadow-focus
```

### 语言切换按钮

```
display: flex
background: --bg-tertiary
border: 1px solid --border-default
border-radius: 7px
overflow: hidden

单个按钮: padding 4px 10px, font-size 12px, font-weight 600
激活: background --accent-blue, color #fff
非激活: color --text-secondary, hover → background --bg-elevated
```

### Toast 通知

```
position: fixed, bottom: 24px, right: 24px
padding: 10px 18px
background: --bg-secondary
border: 1px solid --border-default
border-radius: --radius-lg (10px)
font-size: 13px
max-width: 380px
box-shadow: --shadow-modal
z-index: 999

显示: opacity 0 → 1 (300ms ease)
自动消失: 4000ms
图标颜色: 成功 --accent-green，警告 --accent-yellow，错误 --accent-red
```

### Settings 抽屉

```
width: 340px
从右侧滑入: transform translateX(100%) → translateX(0), 250ms cubic-bezier(.4,0,.2,1)
遮罩: rgba(0,0,0,.45)
背景: --bg-secondary
border-left: 1px solid --border-default
```

---

## 11. 图表规范

**使用 Chart.js CDN（`@4.4.2`）**

### 图表颜色

| 指标 | 暗色 | 亮色 |
|------|------|------|
| 内存 | `#58a6ff` | `#0969da` |
| Swap | `#bc8cff` | `#8250df` |
| CPU  | `#3fb950` | `#1a7f37` |
| 磁盘 | `#d29922` | `#9a6700` |

填充色 = 对应颜色 + alpha 0.1（如 `rgba(88,166,255,.10)`）

### Chart.js 全局选项

```js
{
  animation: false,         // 实时数据不要动画
  responsive: true,
  maintainAspectRatio: false,
  interaction: { mode: 'index', intersect: false },  // 十字准线
  plugins: {
    legend: {
      labels: { color: '#8b949e', boxWidth: 12, font: { size: 11 } }
    }
  },
  scales: {
    x: { display: false },
    y: {
      min: 0, max: 100,
      grid: { color: '#30363d' },    // 亮色: '#e5e7eb'
      ticks: { color: '#8b949e', font: { size: 10 }, callback: v => v + '%' }
    }
  }
}
```

### 图表高度

- 趋势图（监控面板）：150px
- 统计页大图：280px
- 比例图（donut/pie）：240px

---

## 12. 图标规范

- **来源**：项目内联 SVG（不引入外部库）
- **viewBox**：`0 0 16 16`
- **尺寸**：`1em × 1em`（随字体大小缩放）
- **stroke-width**：1.75px（统一）
- **stroke-linecap / linejoin**：round
- **fill**：none（仅线条图标），特殊实心图标用 `fill="currentColor"`
- **颜色**：通过父元素 `color` 继承（`currentColor`）
- **禁止使用 Emoji 替代图标**

### 图标色类

```
.icon-green  → color: --accent-green
.icon-yellow → color: --accent-yellow
.icon-red    → color: --accent-red
.icon-blue   → color: --accent-blue
.icon-muted  → color: --text-secondary
```

---

## 13. 无障碍（Accessibility）

1. **键盘导航**：所有交互元素可 Tab 聚焦，focus ring 2px solid `--border-focus`
2. **对比度**：主文本 ≥4.5:1（WCAG AA），大文字 ≥3:1
3. **语义 HTML**：按钮用 `<button>`，导航用 `<nav>`，表格头用 `<th>`
4. **Aria 标签**：纯图标按钮必须有 `title` 或 `aria-label`
5. **颜色非唯一信息载体**：状态图标 + 颜色同时使用
6. **减少动效**：支持 `prefers-reduced-motion`
7. **Toast 可访问性**：`role="status"` 或 `aria-live="polite"`，不抢焦点
8. **表单标签**：所有输入框有对应 `<label>`

---

## 14. i18n 规范

```js
// 语言 key 格式: "scope.subScope.name"
// 如: "nav.monitor", "proc.safe", "settings.memWarn"

const translations = { zh: {...}, en: {...} };
let _lang = localStorage.getItem('ai-guard-lang') || 'zh';

function t(key, vars) {
  const str = (translations[_lang] || translations.zh)[key] || key;
  if (!vars) return str;
  return str.replace(/\{(\w+)\}/g, (_, k) => vars[k] !== undefined ? vars[k] : '{'+k+'}');
}

function setLang(lang) {
  _lang = lang;
  localStorage.setItem('ai-guard-lang', lang);
  // 更新 UI
}
```

**持久化**：`localStorage.setItem('ai-guard-lang', lang)`  
**默认语言**：中文（`zh`）  
**HTML 标记**：静态文本使用 `data-i18n="key"` 属性，动态内容通过 JS 渲染

---

## 15. 主题切换规范

```js
// 主题存储 key
localStorage.setItem('aigard-theme', 'dark' | 'light');

// 应用方式
document.documentElement.setAttribute('data-theme', theme);

// CSS 选择器
:root, [data-theme="dark"] { /* 暗色变量 */ }
[data-theme="light"] { /* 亮色变量 */ }
```

切换时必须更新：
1. `document.documentElement` 的 `data-theme` 属性
2. Chart.js 图表的 grid/tick/legend 颜色
3. 主题按钮图标（月亮/太阳）

---

## 16. 验收清单

### 视觉
- [ ] 所有页面使用同一套 CSS 变量，无硬编码 hex
- [ ] 无 Emoji 图标，全部使用 SVG
- [ ] 暗色/亮色双主题均通过对比度测试（≥4.5:1）
- [ ] 三个导航 Tab 在所有页面顺序、样式完全一致
- [ ] 卡片圆角 12px，按钮圆角 8px，输入框圆角 6px

### 交互
- [ ] 所有可点击元素有 hover 状态（150ms 过渡）
- [ ] 按钮有 `:active` scale 反馈
- [ ] Focus ring 在键盘导航时可见
- [ ] 主题切换立即生效，含图表颜色
- [ ] 语言切换立即生效，所有文本同步更新

### 功能
- [ ] SSE 实时推流正常（监控面板）
- [ ] 进程视图切换（AI/所有）正常
- [ ] 设置抽屉保存配置后立即生效
- [ ] i18n 持久化到 localStorage
- [ ] 主题持久化到 localStorage

### 性能
- [ ] Chart.js 设置 `animation: false`（实时数据）
- [ ] 进程表 DOM 更新使用 innerHTML 替换（非逐行追加）
- [ ] SSE 断线自动重连（3s 延迟）

---

*最后更新：2026-05-24 · 由 AI Guard Agent 2 维护*
