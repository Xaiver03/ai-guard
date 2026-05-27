"""
原生 NSView 布局构建器 - 构建 Popover UI（iStat Menus 风格）

设计特点：
- 卡片式布局（2×2 网格 + 全宽卡片）
- 信息密度高（主要数值 + 详细信息）
- 视觉层次清晰（大号数值 + 小号详情）
"""
from AppKit import (
    NSTextField, NSButton, NSBox, NSImage,
    NSImageView, NSFont, NSColor, NSRightTextAlignment,
    NSLeftTextAlignment, NSCenterTextAlignment
)


def _semantic_color(percent):
    """根据百分比返回语义颜色"""
    if percent < 50:
        return NSColor.systemGreenColor()
    elif percent < 70:
        return NSColor.systemYellowColor()
    elif percent < 85:
        return NSColor.systemOrangeColor()
    else:
        return NSColor.systemRedColor()


def _format_gb(used, total):
    """格式化 GB 显示"""
    if total >= 100:
        return f"{used:.0f}/{total:.0f}GB"
    else:
        return f"{used:.1f}/{total:.1f}GB"


def build_popover_ui(container, controller):
    """构建 Popover 原生 UI（iStat Menus 风格）

    布局：
    ┌─────────────────────────────────────┐
    │  AI Guard                      70%  │
    ├─────────────────────────────────────┤
    │  ┌───────────┐  ┌───────────┐      │
    │  │ CPU       │  │ Memory    │      │
    │  │ 14%       │  │ 70%       │      │
    │  │ 38.0°C    │  │ 44.8/64GB │      │
    │  └───────────┘  └───────────┘      │
    │  ┌───────────┐  ┌───────────┐      │
    │  │ Swap      │  │ Disk      │      │
    │  │ 60%       │  │ 55%       │      │
    │  │ 3.6/6 GB  │  │ 505/926GB │      │
    │  └───────────┘  └───────────┘      │
    │  ┌─────────────────────────────┐   │
    │  │ Claude Usage                │   │
    │  │ Token 7.1M · $9.81          │   │
    │  └─────────────────────────────┘   │
    │  [一键终止] [自动:关] [完整面板]   │
    └─────────────────────────────────────┘
    """

    W = 320  # 容器宽度（比原来 300px 稍宽）
    PAD = 12  # 外边距
    INNER_W = W - 2 * PAD  # 内容区宽度
    H = 450  # 容器高度

    y = H - 10  # 从顶部开始布局

    metrics_labels = {}
    progress_bars = {}

    # ── 1. 标题栏（紧凑）──────────────────────────────────
    title = _label(((PAD, y - 18), (INNER_W // 2, 18)),
                   "AI Guard",
                   NSFont.systemFontOfSize_weight_(13, 0.6),
                   NSColor.labelColor())
    container.addSubview_(title)

    # 当前内存百分比（右对齐）
    mem_badge = _label(((W - PAD - 60, y - 18), (60, 18)),
                       "70%",
                       NSFont.monospacedSystemFontOfSize_weight_(13, 0.6),
                       NSColor.secondaryLabelColor(),
                       NSRightTextAlignment)
    metrics_labels['mem_badge'] = mem_badge
    container.addSubview_(mem_badge)

    y -= 28

    # 分隔线
    sep = NSBox.alloc().initWithFrame_(((0, y), (W, 1)))
    sep.setBoxType_(3)  # NSBoxSeparator
    container.addSubview_(sep)
    y -= 16

    # ── 2. 卡片区（2×2 网格）──────────────────────────────
    CARD_W = 140
    CARD_H = 80
    GAP = 10

    # 卡片配置：(key, title, x, y)
    card_configs = [
        ('cpu', 'CPU', PAD, y - CARD_H),
        ('mem', 'Memory', PAD + CARD_W + GAP, y - CARD_H),
        ('swap', 'Swap', PAD, y - CARD_H * 2 - GAP),
        ('disk', 'Disk', PAD + CARD_W + GAP, y - CARD_H * 2 - GAP),
    ]

    for key, title_text, x, card_y in card_configs:
        # 创建卡片容器
        card = NSBox.alloc().initWithFrame_(((x, card_y), (CARD_W, CARD_H)))
        card.setBoxType_(4)  # NSBoxCustom
        card.setCornerRadius_(10)
        card.setFillColor_(NSColor.secondarySystemFillColor())
        card.setBorderWidth_(0)
        card.setTitlePosition_(0)  # NSNoTitle
        container.addSubview_(card)

        # 卡片内布局
        card_pad = 10

        # 标题（小号，次要色）
        title_lbl = _label(((card_pad, CARD_H - card_pad - 14), (CARD_W - 2 * card_pad, 14)),
                           title_text,
                           NSFont.systemFontOfSize_weight_(10, 0.5),
                           NSColor.secondaryLabelColor())
        card.addSubview_(title_lbl)

        # 主要数值（大号，高对比度）
        value_lbl = _label(((card_pad, CARD_H - card_pad - 42), (CARD_W - 2 * card_pad, 28)),
                           "0%",
                           NSFont.monospacedSystemFontOfSize_weight_(24, 0.6),
                           NSColor.labelColor())
        metrics_labels[key] = value_lbl
        card.addSubview_(value_lbl)

        # 详细信息（小号，次要色）
        detail_lbl = _label(((card_pad, card_pad), (CARD_W - 2 * card_pad, 14)),
                            "",
                            NSFont.monospacedSystemFontOfSize_weight_(10, 0.3),
                            NSColor.tertiaryLabelColor())
        metrics_labels[f'{key}_detail'] = detail_lbl
        card.addSubview_(detail_lbl)

    y -= CARD_H * 2 + GAP + 16

    # ── 3. Claude 使用统计卡片（全宽）──────────────────────
    claude_card = NSBox.alloc().initWithFrame_(((PAD, y - 60), (INNER_W, 60)))
    claude_card.setBoxType_(4)
    claude_card.setCornerRadius_(10)
    claude_card.setFillColor_(NSColor.secondarySystemFillColor())
    claude_card.setBorderWidth_(0)
    claude_card.setTitlePosition_(0)
    container.addSubview_(claude_card)

    # 标题
    claude_title = _label(((10, 60 - 10 - 14), (INNER_W - 60, 14)),
                          "Claude Usage",
                          NSFont.systemFontOfSize_weight_(10, 0.5),
                          NSColor.secondaryLabelColor())
    claude_card.addSubview_(claude_title)

    # 刷新按钮（右上角）
    refresh_btn = NSButton.alloc().initWithFrame_(((INNER_W - 32, 60 - 10 - 22), (28, 22)))
    refresh_img = NSImage.imageWithSystemSymbolName_accessibilityDescription_(
        "arrow.clockwise", "Refresh"
    )
    if refresh_img:
        refresh_btn.setImage_(refresh_img)
        refresh_btn.setImagePosition_(1)  # NSImageOnly
    else:
        refresh_btn.setTitle_("↻")
    refresh_btn.setBezelStyle_(1)
    refresh_btn.setBordered_(False)
    refresh_btn.setTarget_(controller)
    refresh_btn.setAction_("refreshUsage:")
    claude_card.addSubview_(refresh_btn)

    # 使用统计（大号）
    usage_lbl = _label(((10, 10), (INNER_W - 20, 28)),
                       "Token 0 · $0.00",
                       NSFont.monospacedSystemFontOfSize_weight_(14, 0.5),
                       NSColor.labelColor())
    metrics_labels['usage'] = usage_lbl
    claude_card.addSubview_(usage_lbl)

    y -= 76

    # ── 4. 快捷按钮行 ──────────────────────────────────────
    btn_w = (INNER_W - GAP * 2) // 3
    btn_h = 28

    kill_btn = _compact_button(
        ((PAD, y), (btn_w, btn_h)),
        "一键终止",
        controller, "killSafeProcesses:"
    )
    container.addSubview_(kill_btn)

    autokill_btn = _compact_button(
        ((PAD + btn_w + GAP, y), (btn_w, btn_h)),
        "自动:关",
        controller, "toggleAutokill:"
    )
    metrics_labels['autokill_btn'] = autokill_btn
    container.addSubview_(autokill_btn)

    dashboard_btn = _compact_button(
        ((PAD + (btn_w + GAP) * 2, y), (btn_w, btn_h)),
        "完整面板",
        controller, "openDashboard:"
    )
    container.addSubview_(dashboard_btn)

    y -= 38

    # ── 5. 状态标签（用于显示操作反馈）──────────────────────
    status_label = _label(
        ((PAD, y), (INNER_W, 16)),
        "",
        NSFont.systemFontOfSize_(10),
        NSColor.secondaryLabelColor(),
        NSCenterTextAlignment
    )
    container.addSubview_(status_label)
    metrics_labels['status'] = status_label

    return metrics_labels, progress_bars


# ── 辅助函数 ──────────────────────────────────────────────

def _label(frame, text, font, color, alignment=None):
    """创建 NSTextField 标签"""
    lbl = NSTextField.alloc().initWithFrame_(frame)
    lbl.setStringValue_(text)
    lbl.setFont_(font)
    lbl.setTextColor_(color)
    lbl.setBezeled_(False)
    lbl.setDrawsBackground_(False)
    lbl.setEditable_(False)
    lbl.setSelectable_(False)
    if alignment:
        lbl.setAlignment_(alignment)
    return lbl


def _compact_button(frame, title, target, action):
    """创建紧凑按钮"""
    btn = NSButton.alloc().initWithFrame_(frame)
    btn.setTitle_(title)
    btn.setBezelStyle_(1)  # NSBezelStyleRounded
    btn.setFont_(NSFont.systemFontOfSize_(11))
    btn.setTarget_(target)
    btn.setAction_(action)
    return btn
