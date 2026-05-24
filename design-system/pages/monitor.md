# AI Guard — 监控面板页面规范

> 继承自 `design-system/MASTER.md`，以下为 index.html 特有规则。

## 特有组件

### 资源仪表（Gauge）

- 4 个仪表：内存 / Swap / 磁盘 / CPU
- 进度条高度 8px，`border-radius: full`
- **颜色动态切换规则**（JS 控制，使用 CSS 变量）：
  - `pct >= 90` → `var(--accent-red)`
  - `pct >= 70` → `var(--accent-yellow)`
  - `pct <  70` → `var(--accent-green)`
- 进度条宽度过渡：`transition: width 300ms ease-out, background 300ms`

### 趋势图（Chart.js）

- 高度：150px（`.chart-wrap`）
- 内存线：`var(--chart-memory)` = `#58a6ff`
- Swap 线：`var(--chart-swap)` = `#bc8cff`
- CPU 线：`var(--chart-cpu)` = `#3fb950`
- 磁盘线：`var(--chart-disk)` = `#d29922`
- 填充色：对应线色 + `rgba(..., .10)`
- `animation: false`（实时数据禁动画）
- 主题切换时需同步更新 grid/tick/legend 颜色

### 进程表

- 视图切换：AI/开发进程 | 所有进程
- "所有进程"视图：每 5 秒轮询 `/api/processes/all`
- 风险等级图标 + 文字同时显示（颜色非唯一语义）
- 批量操作栏固定在表格上方

### SSE 实时推流

- 端点：`/api/stream`
- 断线自动重连，延迟 3000ms
- 只在 AI 视图下自动更新进程列表

## 不得修改的行为

- `SIGSTOP / SIGCONT / SIGTERM` 操作逻辑
- 白名单 / 黑名单管理 API 调用
- 设置抽屉保存流程
- SSE 事件解析结构
