# AI Guard — 书签管理页面规范

> 继承自 `design-system/MASTER.md`，以下为 bookmarks.html 特有规则。

## 特有组件

### 统计概览卡片行

- 书签总数 / 文件夹数 / 已分析数
- 样式同 `.metric-card`

### 搜索 / 筛选栏

- 搜索输入框：`input[type="search"]`，宽度 `min(280px, 100%)`
- 文件夹筛选：下拉 `<select>` 或按钮组
- 位于书签列表上方，卡片内

### 书签列表

- 默认视图：卡片网格（2 列桌面，1 列移动）
- 可选表格视图（切换按钮）
- 每条书签：favicon 图标位置留 16×16 区域，无图时用占位图标

### AI 分析区域

- 分析按钮：触发 `POST /api/bookmarks/analyze`
- 结果显示：分析结论卡片，`border-left: 3px solid var(--accent-blue)`
- 加载状态：`.spinner` 组件
- 错误状态：`.badge-warn` + 重试按钮

## API 端点

- `GET /api/bookmarks` — 书签列表（含 Safari 书签）
- `POST /api/bookmarks/analyze` — AI 分析

## 注意

- Safari 书签需要用户授权，无权限时显示友好提示
- 书签 URL 安全打开（`target="_blank" rel="noopener noreferrer"`）
