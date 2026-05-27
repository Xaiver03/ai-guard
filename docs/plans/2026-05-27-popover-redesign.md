# Popover 面板重新设计方案

**日期：** 2026-05-27  
**目标：** 参考 iStat Menus 风格，重新设计 Popover 面板

---

## 设计参考

### iStat Menus 特点
- **卡片式布局**：每个指标独立卡片，圆角 8-12px
- **信息密度高**：主要数值 + 详细信息 + 实时图表
- **视觉层次**：
  - 标题：小号字体，次要颜色
  - 主要数值：大号字体，高对比度
  - 详细信息：小号字体，次要颜色
- **深色毛玻璃背景**：半透明，适配深色/浅色模式
- **紧凑布局**：卡片间距 8-12px

---

## 新布局设计

```
┌─────────────────────────────────────┐
│  AI Guard                      70%  │  ← 标题栏（紧凑）
├─────────────────────────────────────┤
│  ┌───────────┐  ┌───────────┐      │
│  │ CPU       │  │ Memory    │      │  ← 卡片行 1
│  │ 14%       │  │ 70%       │      │
│  │ 38.0°C    │  │ 44.8/64GB │      │
│  └───────────┘  └───────────┘      │
│                                     │
│  ┌───────────┐  ┌───────────┐      │
│  │ Swap      │  │ Disk      │      │  ← 卡片行 2
│  │ 60%       │  │ 55%       │      │
│  │ 3.6/6 GB  │  │ 505/926GB │      │
│  └───────────┘  └───────────┘      │
│                                     │
│  ┌─────────────────────────────┐   │
│  │ Claude Usage                │   │  ← Claude 统计卡片
│  │ Token 7.1M · $9.81          │   │
│  └─────────────────────────────┘   │
│                                     │
│  [一键终止] [自动:关] [完整面板]   │  ← 快捷按钮
└─────────────────────────────────────┘
```

---

## 尺寸规格

- **容器宽度**：320px（比原来 300px 稍宽）
- **容器高度**：自适应（约 400-450px）
- **卡片尺寸**：
  - 小卡片（CPU/Mem/Swap/Disk）：140×80px
  - 大卡片（Claude Usage）：全宽×60px
- **间距**：
  - 外边距：12px
  - 卡片间距：10px
  - 卡片内边距：10px
- **圆角**：10px

---

## 颜色方案

### 深色模式
- **背景**：`NSColor.controlBackgroundColor()`（系统自适应）
- **卡片背景**：`NSColor.secondarySystemFillColor()`（半透明）
- **主要文字**：`NSColor.labelColor()`
- **次要文字**：`NSColor.secondaryLabelColor()`
- **强调色**：
  - 正常：`NSColor.systemGreenColor()`
  - 警告：`NSColor.systemOrangeColor()`
  - 危险：`NSColor.systemRedColor()`

---

## 字体规格

- **标题**：SF Pro Text, 11pt, Medium
- **主要数值**：SF Pro Display, 24pt, Semibold
- **次要数值**：SF Mono, 11pt, Regular
- **详细信息**：SF Pro Text, 10pt, Regular

---

## 实现步骤

### Phase 1：基础布局（优先）
1. 修改容器尺寸：320×450px
2. 实现卡片容器（NSBox with rounded corners）
3. 布局 4 个小卡片（2×2 网格）
4. 布局 Claude 统计大卡片
5. 布局快捷按钮行

### Phase 2：数据绑定
1. CPU 卡片：百分比 + 温度（如果可获取）
2. Memory 卡片：百分比 + 已用/总量
3. Swap 卡片：百分比 + 已用/总量
4. Disk 卡片：百分比 + 已用/总量
5. Claude 卡片：Token 数量 + 费用

### Phase 3：视觉优化
1. 添加语义颜色（根据百分比）
2. 添加 SF Symbol 图标（小号，次要色）
3. 优化字体层次
4. 添加卡片阴影/边框

### Phase 4：交互优化（可选）
1. 卡片点击展开详情
2. 添加迷你图表（sparkline）
3. 添加动画过渡

---

## 技术实现

### 卡片容器（NSBox）

```python
def _create_card(frame, title, value, detail):
    """创建圆角卡片"""
    card = NSBox.alloc().initWithFrame_(frame)
    card.setBoxType_(4)  # NSBoxCustom
    card.setCornerRadius_(10)
    card.setFillColor_(NSColor.secondarySystemFillColor())
    card.setBorderWidth_(0)
    
    # 添加标题
    title_label = _label(...)
    card.addSubview_(title_label)
    
    # 添加主要数值
    value_label = _label(...)
    card.addSubview_(value_label)
    
    # 添加详细信息
    detail_label = _label(...)
    card.addSubview_(detail_label)
    
    return card
```

### 网格布局

```python
# 2×2 网格布局
card_w = 140
card_h = 80
gap = 10

cards = [
    ('cpu', 'CPU', PAD, y),
    ('mem', 'Memory', PAD + card_w + gap, y),
    ('swap', 'Swap', PAD, y - card_h - gap),
    ('disk', 'Disk', PAD + card_w + gap, y - card_h - gap),
]

for key, title, x, y in cards:
    card = _create_card((x, y, card_w, card_h), title, ...)
    container.addSubview_(card)
```

---

## 兼容性

- **macOS 版本**：10.14+ (NSBox.setCornerRadius_ 需要 10.14+)
- **降级方案**：如果 API 不可用，使用普通矩形 + 分隔线

---

## 预期效果

- **信息密度**：从 4 行指标 → 6 个卡片（更紧凑）
- **可读性**：大号数值 + 清晰层次（更易读）
- **美观度**：卡片式 + 圆角 + 阴影（更现代）
- **一致性**：与 iStat Menus 风格接近（用户熟悉）
