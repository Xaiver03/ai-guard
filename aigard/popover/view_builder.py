"""
原生 NSView 布局构建器 - 构建 Popover UI

参考设计：iStatistica Pro 风格
- 语义颜色进度条（绿/黄/橙/红）
- SF Symbols 图标
- 详细数值（XX.X / YY.Y GB 格式）
"""
from AppKit import (
    NSTextField, NSProgressIndicator, NSButton, NSBox, NSImage,
    NSImageView, NSFont, NSColor, NSRightTextAlignment,
    NSLeftTextAlignment, NSCenterTextAlignment
)


# ── 语义颜色 ──────────────────────────────────────────────
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
        return f"{used:.0f} / {total:.0f} GB"
    else:
        return f"{used:.1f} / {total:.1f} GB"


def build_popover_ui(container, controller):
    """构建 Popover 原生 UI（纯 AppKit 控件）

    布局：
    ┌────────────────────────────────┐
    │  🛡 AI Guard Status            │  ← 标题 + SF Symbol
    ├────────────────────────────────┤
    │  ▸ CPU     13%  ██░░░░░░░░░   │  ← 指标区（语义颜色 + 详细值）
    │            8.3 / 64.0 GB      │
    │  ▸ Memory  64%  █████████░░   │
    │            41.0 / 64.0 GB     │
    │  ▸ Swap    74%  ██████████░   │
    │            4.4 / 6.0 GB       │
    │  ▸ Disk    55%  ██████░░░░░   │
    │            504.8 / 926.4 GB   │
    ├────────────────────────────────┤
    │  ✦ Token 838.0M · $4368.25 ↻  │  ← Claude 统计
    ├────────────────────────────────┤
    │  [🔪 一键终止]  [⚡ 自动: 关]  │  ← 快捷按钮
    │  [📊 打开完整面板]             │
    │  [退出 AI Guard]               │
    └────────────────────────────────┘
    """

    W = 300  # 容器宽度
    PAD = 14  # 边距
    INNER_W = W - 2 * PAD  # 内容区宽度
    H = 480  # 容器高度

    y = H - 10  # 从顶部开始布局（留 10px 顶部边距）

    metrics_labels = {}
    progress_bars = {}

    # ── 1. 标题栏 ──────────────────────────────────────────
    # SF Symbol 图标
    shield_img = NSImage.imageWithSystemSymbolName_accessibilityDescription_(
        "shield.fill", "AI Guard"
    )
    if shield_img:
        icon_view = NSImageView.alloc().initWithFrame_(((PAD, y - 20), (18, 18)))
        icon_view.setImage_(shield_img)
        icon_view.setContentTintColor_(NSColor.systemBlueColor())
        container.addSubview_(icon_view)

    title = _label(((PAD + 22, y - 22), (INNER_W - 22, 22)),
                   "AI Guard Status",
                   NSFont.systemFontOfSize_weight_(14, 0.6),
                   NSColor.labelColor())
    container.addSubview_(title)
    y -= 32

    # 分隔线
    container.addSubview_(_separator(y, W))
    y -= 16

    # ── 2. 系统指标区（4 组，每组 2 行）──────────────────────
    metric_configs = [
        ('cpu', 'CPU', 'cpu.fill'),
        ('mem', 'Memory', 'memorychip'),
        ('swap', 'Swap', 'arrow.triangle.swap'),
        ('disk', 'Disk', 'internaldrive.fill'),
    ]

    for key, text, sf_name in metric_configs:
        # SF Symbol 图标
        sym_img = NSImage.imageWithSystemSymbolName_accessibilityDescription_(sf_name, text)
        if sym_img:
            sym_view = NSImageView.alloc().initWithFrame_(((PAD, y - 1), (14, 14)))
            sym_view.setImage_(sym_img)
            sym_view.setContentTintColor_(NSColor.secondaryLabelColor())
            container.addSubview_(sym_view)

        # 名称标签
        container.addSubview_(_label(
            ((PAD + 18, y), (55, 16)), text,
            NSFont.systemFontOfSize_weight_(11, 0.5), NSColor.labelColor()
        ))

        # 百分比标签（右对齐）
        val_label = _label(((W - PAD - 50, y), (50, 16)), "0%",
                     NSFont.monospacedSystemFontOfSize_weight_(12, 0.6),
                     NSColor.labelColor(),
                     alignment=NSRightTextAlignment)
        metrics_labels[key] = val_label
        container.addSubview_(val_label)

        y -= 18

        # 进度条（加宽）
        progress = NSProgressIndicator.alloc().initWithFrame_(((PAD + 18, y + 2), (INNER_W - 68, 6)))
        progress.setStyle_(0)  # bar
        progress.setIndeterminate_(False)
        progress.setMinValue_(0)
        progress.setMaxValue_(100)
        progress_bars[key] = progress
        container.addSubview_(progress)

        y -= 14

        # 详细数值标签（第二行）
        detail_label = _label(((PAD + 18, y), (INNER_W - 18, 14)), "",
                     NSFont.monospacedSystemFontOfSize_weight_(10, 0.3),
                     NSColor.tertiaryLabelColor())
        metrics_labels[f'{key}_detail'] = detail_label
        container.addSubview_(detail_label)

        y -= 20

    y -= 4

    # ── 3. 分隔线 ──────────────────────────────────────────
    container.addSubview_(_separator(y, W))
    y -= 16

    # ── 4. Claude 使用统计 + 刷新按钮 ──────────────────────
    # Token 图标
    token_img = NSImage.imageWithSystemSymbolName_accessibilityDescription_(
        "sparkle", "Token"
    )
    if token_img:
        token_icon = NSImageView.alloc().initWithFrame_(((PAD, y - 1), (14, 14)))
        token_icon.setImage_(token_img)
        token_icon.setContentTintColor_(NSColor.systemPurpleColor())
        container.addSubview_(token_icon)

    usage_lbl = _label(((PAD + 18, y), (INNER_W - 50, 16)), "Token 0 · $0.00",
                       NSFont.systemFontOfSize_(11), NSColor.secondaryLabelColor())
    metrics_labels['usage'] = usage_lbl
    container.addSubview_(usage_lbl)

    # 刷新按钮（使用 SF Symbol）
    refresh_btn = NSButton.alloc().initWithFrame_(((W - PAD - 32, y - 4), (32, 22)))
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
    container.addSubview_(refresh_btn)

    y -= 28

    # ── 5. 分隔线 ──────────────────────────────────────────
    container.addSubview_(_separator(y, W))
    y -= 16

    # ── 6. 快捷按钮区 ──────────────────────────────────────
    kill_btn = _icon_button(
        ((PAD, y), (INNER_W // 2 - 4, 30)),
        "一键终止", "xmark.circle.fill",
        NSColor.systemRedColor(),
        controller, "killSafeProcesses:"
    )
    container.addSubview_(kill_btn)

    autokill_btn = _icon_button(
        ((PAD + INNER_W // 2 + 4, y), (INNER_W // 2 - 4, 30)),
        "自动: 关", "bolt.fill",
        NSColor.systemYellowColor(),
        controller, "toggleAutokill:"
    )
    metrics_labels['autokill_btn'] = autokill_btn
    container.addSubview_(autokill_btn)
    y -= 38

    dashboard_btn = _icon_button(
        ((PAD, y), (INNER_W, 30)),
        "打开完整面板", "chart.bar.xaxis",
        NSColor.systemBlueColor(),
        controller, "openDashboard:"
    )
    container.addSubview_(dashboard_btn)
    y -= 38

    quit_btn = _icon_button(
        ((PAD, y), (INNER_W, 30)),
        "退出 AI Guard", "power",
        NSColor.secondaryLabelColor(),
        controller, "quitApp:"
    )
    container.addSubview_(quit_btn)
    y -= 38

    # ── 7. 状态标签（用于显示操作反馈）──────────────────────
    status_label = _label(
        ((PAD, y), (INNER_W, 20)),
        "",  # 初始为空
        NSFont.systemFontOfSize_(11),
        NSColor.secondaryLabelColor(),
        NSCenterTextAlignment
    )
    container.addSubview_(status_label)
    metrics_labels['status'] = status_label

    # 调整容器高度（不改变，保持初始值）

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


def _separator(y, width):
    """创建分隔线"""
    sep = NSBox.alloc().initWithFrame_(((0, y), (width, 1)))
    sep.setBoxType_(3)  # NSBoxSeparator
    return sep


def _button(frame, title, target, action):
    """创建 NSButton"""
    btn = NSButton.alloc().initWithFrame_(frame)
    btn.setTitle_(title)
    btn.setBezelStyle_(1)  # NSBezelStyleRounded
    btn.setTarget_(target)
    btn.setAction_(action)
    return btn


def _icon_button(frame, title, sf_symbol_name, tint_color, target, action):
    """创建带 SF Symbol 图标的 NSButton"""
    btn = NSButton.alloc().initWithFrame_(frame)
    btn.setTitle_(f"  {title}")
    btn.setBezelStyle_(1)  # NSBezelStyleRounded
    btn.setFont_(NSFont.systemFontOfSize_(12))

    # 添加 SF Symbol 图标
    img = NSImage.imageWithSystemSymbolName_accessibilityDescription_(sf_symbol_name, title)
    if img:
        btn.setImage_(img)
        btn.setImagePosition_(2)  # NSImageLeft
        btn.setContentTintColor_(tint_color)

    btn.setTarget_(target)
    btn.setAction_(action)
    return btn
