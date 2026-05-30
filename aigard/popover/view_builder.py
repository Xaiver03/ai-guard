"""
# [CN] 原生 NSView 布局构建器 - 遵循 AI Guard 设计系统

# [CN] 设计规范:
# [CN] - 简洁黑白配色 + 语义色(仅用于警告)
# [CN] - 间距: 4px 基准 (space-2=8px, space-3=12px, space-4=16px)
# [CN] - 圆角: radius-xl=12px (卡片), radius-md=8px (按钮)
# [CN] - 字体: text-xs=11px, text-sm=13px, text-2xl=24px
# [CN] - 磨砂玻璃背景
# [CN] - 禁止 Emoji,使用纯文本
"""
from AppKit import (
    NSTextField, NSButton, NSBox, NSView,
    NSFont, NSColor, NSRightTextAlignment,
    NSLeftTextAlignment, NSCenterTextAlignment,
    NSProgressIndicator, NSProgressIndicatorStyleBar,
    NSVisualEffectView, NSVisualEffectMaterialPopover, NSVisualEffectBlendingModeBehindWindow,
    NSAttributedString, NSForegroundColorAttributeName
)
from Foundation import NSRect, NSPoint, NSDictionary


# ============================================================
# [CN] 设计令牌 (Design Tokens)
# ============================================================

class DesignTokens:
    # [CN] """设计系统令牌 - 简洁黑白配色"""

    # [CN] # 间距 (4px 基准)
    # [CN] SPACE_2 = 8.0   # 小间距
    # [CN] SPACE_3 = 12.0  # 中间距
    # [CN] SPACE_4 = 16.0  # 标准间距

    # [CN] # 圆角
    # [CN] RADIUS_MD = 8.0   # 按钮
    # [CN] RADIUS_XL = 12.0  # 卡片

    # [CN] # 字体大小
    # [CN] TEXT_XS = 11.0   # 辅助信息
    TEXT_SM = 13.0   # Body
    # [CN] TEXT_2XL = 28.0  # 数值 (加大)

    # [CN] # 字重
    WEIGHT_NORMAL = 0.0    # 400
    WEIGHT_MEDIUM = 0.23   # 500
    WEIGHT_SEMIBOLD = 0.3  # 600

    # [CN] # 颜色 - 简洁黑白配色 + 语义色
    # [CN] TEXT_PRIMARY = NSColor.labelColor()           # 系统主文本色 (自动适配亮暗)
    # [CN] TEXT_SECONDARY = NSColor.secondaryLabelColor()  # 系统次要文本色
    # [CN] TEXT_TERTIARY = NSColor.tertiaryLabelColor()    # 系统三级文本色

    # [CN] # 语义色 (用于数值和警告)
    ACCENT_BLUE = NSColor.systemBlueColor()      # NormalState
    # [CN] ACCENT_GREEN = NSColor.systemGreenColor()    # 良好状态
    ACCENT_YELLOW = NSColor.systemYellowColor()  # Warning
    # [CN] ACCENT_RED = NSColor.systemRedColor()        # 危险


def _create_card(frame, corner_radius=None):
    # [CN] """创建圆角卡片"""
    if corner_radius is None:
        corner_radius = DesignTokens.RADIUS_XL

    card = NSBox.alloc().initWithFrame_(frame)
    card.setBoxType_(4)  # NSBoxCustom
    card.setCornerRadius_(corner_radius)
    card.setFillColor_(NSColor.controlBackgroundColor())  # [CN] 系统卡片背景色
    card.setBorderWidth_(0)
    card.setTitlePosition_(0)
    return card


def _label(frame, text, font, color, alignment=NSLeftTextAlignment):
    # [CN] """创建文本标签"""
    label = NSTextField.alloc().initWithFrame_(frame)
    label.setStringValue_(text)
    label.setFont_(font)
    label.setTextColor_(color)
    label.setAlignment_(alignment)
    label.setBezeled_(False)
    label.setDrawsBackground_(False)
    label.setEditable_(False)
    label.setSelectable_(False)
    return label


def _progress_bar(frame):
    # [CN] """创建进度条"""
    bar = NSProgressIndicator.alloc().initWithFrame_(frame)
    bar.setStyle_(NSProgressIndicatorStyleBar)
    bar.setIndeterminate_(False)
    bar.setMinValue_(0)
    bar.setMaxValue_(100)
    bar.setDoubleValue_(0)
    return bar


def _semantic_color(percent):
    # [CN] """根据百分比返回语义颜色"""
    if percent >= 85:
        return DesignTokens.ACCENT_RED
    elif percent >= 70:
        return DesignTokens.ACCENT_YELLOW
    elif percent >= 50:
        return DesignTokens.ACCENT_BLUE
    else:
        return DesignTokens.ACCENT_GREEN


def _format_gb(used, total):
    # [CN] """格式化 GB 显示"""
    if total >= 100:
        return f"{used:.0f}/{total:.0f}GB"
    else:
        return f"{used:.1f}/{total:.1f}GB"


def build_popover_ui(container, controller):
    # [CN] """构建 Popover 原生 UI - 仿 iStat Menus 风格

    # [CN] 尺寸: 360×550px (增加高度以容纳折线图)
    """
    from AppKit import NSVisualEffectView, NSVisualEffectMaterialPopover, NSVisualEffectBlendingModeBehindWindow

    W = 360.0
    H = 550.0  # [CN] 增加高度
    PAD = DesignTokens.SPACE_4  # 16px
    GAP = DesignTokens.SPACE_3  # 12px

    # [CN] 渐变磨砂玻璃背景
    blur_view = NSVisualEffectView.alloc().initWithFrame_(((0, 0), (W, H)))
    blur_view.setMaterial_(NSVisualEffectMaterialPopover)
    blur_view.setBlendingMode_(NSVisualEffectBlendingModeBehindWindow)
    blur_view.setState_(1)
    container.addSubview_(blur_view)

    metrics_labels = {}
    progress_bars = {}

    # [CN] 卡片尺寸 - 合理的高度
    card_w = (W - 2 * PAD - GAP) / 2.0  # 156px
    card_h = 110.0  # [CN] 固定高度
    claude_card_h = 160.0  # [CN] Claude 卡片更高,容纳折线图

    y = H - PAD  # [CN] 从顶部开始

    # [CN] ── 1. CPU 卡片 ──
    cpu_card = _create_card(((PAD, y - card_h), (card_w, card_h)))
    blur_view.addSubview_(cpu_card)

    cpu_title = _label(
        ((DesignTokens.SPACE_3, card_h - DesignTokens.SPACE_3 - 16), (card_w - DesignTokens.SPACE_3 * 2, 16)),
        "CPU",
        NSFont.systemFontOfSize_weight_(DesignTokens.TEXT_SM, DesignTokens.WEIGHT_SEMIBOLD),
        DesignTokens.TEXT_SECONDARY
    )
    cpu_card.addSubview_(cpu_title)

    cpu_value = _label(
        ((DesignTokens.SPACE_3, card_h - DesignTokens.SPACE_3 - 50), (card_w - DesignTokens.SPACE_3 * 2, 32)),
        "0%",
        NSFont.systemFontOfSize_weight_(DesignTokens.TEXT_2XL, DesignTokens.WEIGHT_SEMIBOLD),
        DesignTokens.TEXT_PRIMARY
    )
    metrics_labels['cpu'] = cpu_value
    cpu_card.addSubview_(cpu_value)

    cpu_detail = _label(
        ((DesignTokens.SPACE_3, DesignTokens.SPACE_2), (card_w - DesignTokens.SPACE_3 * 2, 14)),
        "Apple M4 Max",
        NSFont.systemFontOfSize_(DesignTokens.TEXT_XS),
        DesignTokens.TEXT_TERTIARY
    )
    cpu_card.addSubview_(cpu_detail)

    # [CN] ── 2. 磁盘卡片 ──
    disk_card = _create_card(((PAD + card_w + GAP, y - card_h), (card_w, card_h)))
    blur_view.addSubview_(disk_card)

    disk_title = _label(
        ((DesignTokens.SPACE_3, card_h - DesignTokens.SPACE_3 - 16), (card_w - DesignTokens.SPACE_3 * 2, 16)),
        "磁盘",
        NSFont.systemFontOfSize_weight_(DesignTokens.TEXT_SM, DesignTokens.WEIGHT_SEMIBOLD),
        DesignTokens.TEXT_SECONDARY
    )
    disk_card.addSubview_(disk_title)

    disk_value = _label(
        ((DesignTokens.SPACE_3, card_h - DesignTokens.SPACE_3 - 50), (card_w - DesignTokens.SPACE_3 * 2, 32)),
        "0%",
        NSFont.systemFontOfSize_weight_(DesignTokens.TEXT_2XL, DesignTokens.WEIGHT_SEMIBOLD),
        DesignTokens.TEXT_PRIMARY
    )
    metrics_labels['disk'] = disk_value
    disk_card.addSubview_(disk_value)

    disk_detail = _label(
        ((DesignTokens.SPACE_3, DesignTokens.SPACE_2 + 16), (card_w - DesignTokens.SPACE_3 * 2, 14)),
        "504/926GB",
        NSFont.systemFontOfSize_(DesignTokens.TEXT_XS),
        DesignTokens.TEXT_TERTIARY
    )
    metrics_labels['disk_detail'] = disk_detail
    disk_card.addSubview_(disk_detail)

    # [CN] 磁盘 I/O 速度
    disk_io = _label(
        ((DesignTokens.SPACE_3, DesignTokens.SPACE_2), (card_w - DesignTokens.SPACE_3 * 2, 14)),
        "R: 0 KB/s  W: 0 KB/s",
        NSFont.systemFontOfSize_(DesignTokens.TEXT_XS),
        DesignTokens.TEXT_TERTIARY
    )
    metrics_labels['disk_io'] = disk_io
    disk_card.addSubview_(disk_io)

    # [CN] ── 3. 内存卡片 ──
    # [CN] 注意:内存卡片在左侧,使用 card_h
    # [CN] Claude 卡片在右侧,使用 claude_card_h (更高)
    # [CN] 所以这里 y 要减去较大的高度,确保下一行对齐
    y -= max(card_h, claude_card_h) + GAP

    ram_card = _create_card(((PAD, y - card_h), (card_w, card_h)))
    blur_view.addSubview_(ram_card)

    ram_title = _label(
        ((DesignTokens.SPACE_3, card_h - DesignTokens.SPACE_3 - 16), (card_w - DesignTokens.SPACE_3 * 2, 16)),
        "内存",
        NSFont.systemFontOfSize_weight_(DesignTokens.TEXT_SM, DesignTokens.WEIGHT_SEMIBOLD),
        DesignTokens.TEXT_SECONDARY
    )
    ram_card.addSubview_(ram_title)

    ram_detail = _label(
        ((DesignTokens.SPACE_3, card_h - DesignTokens.SPACE_3 - 36), (card_w - DesignTokens.SPACE_3 * 2, 14)),
        "62.0/64.0GB",
        NSFont.systemFontOfSize_(DesignTokens.TEXT_XS),
        DesignTokens.TEXT_SECONDARY
    )
    metrics_labels['mem_detail'] = ram_detail
    ram_card.addSubview_(ram_detail)

    ram_bar = _progress_bar(
        ((DesignTokens.SPACE_3, card_h - DesignTokens.SPACE_3 - 52), (card_w - DesignTokens.SPACE_3 * 2, 6))
    )
    progress_bars['mem'] = ram_bar
    ram_card.addSubview_(ram_bar)

    swap_label = _label(
        ((DesignTokens.SPACE_3, DesignTokens.SPACE_2), (40, 14)),
        "Swap",
        NSFont.systemFontOfSize_(DesignTokens.TEXT_XS),
        DesignTokens.TEXT_TERTIARY
    )
    ram_card.addSubview_(swap_label)

    swap_value = _label(
        ((50, DesignTokens.SPACE_2), (card_w - 50 - DesignTokens.SPACE_3, 14)),
        "55%",
        NSFont.systemFontOfSize_(DesignTokens.TEXT_XS),
        DesignTokens.TEXT_SECONDARY,
        NSRightTextAlignment
    )
    metrics_labels['swap'] = swap_value
    ram_card.addSubview_(swap_value)

    # [CN] ── 4. Claude 卡片 (显示更多信息 + 折线图) ──
    claude_card = _create_card(((PAD + card_w + GAP, y - claude_card_h), (card_w, claude_card_h)))
    blur_view.addSubview_(claude_card)

    claude_title = _label(
        ((DesignTokens.SPACE_3, claude_card_h - DesignTokens.SPACE_3 - 16), (card_w - DesignTokens.SPACE_3 * 2, 16)),
        "Claude 今日",
        NSFont.systemFontOfSize_weight_(DesignTokens.TEXT_SM, DesignTokens.WEIGHT_SEMIBOLD),
        DesignTokens.TEXT_SECONDARY
    )
    claude_card.addSubview_(claude_title)

    # Token Count
    usage_token = _label(
        ((DesignTokens.SPACE_3, claude_card_h - DesignTokens.SPACE_3 - 36), (card_w - DesignTokens.SPACE_3 * 2, 14)),
        "Token: 26.3M",
        NSFont.systemFontOfSize_(DesignTokens.TEXT_XS),
        DesignTokens.TEXT_PRIMARY
    )
    metrics_labels['usage_token'] = usage_token
    claude_card.addSubview_(usage_token)

    # [CN] 费用
    usage_cost = _label(
        ((DesignTokens.SPACE_3, claude_card_h - DesignTokens.SPACE_3 - 52), (card_w - DesignTokens.SPACE_3 * 2, 14)),
        "费用: $41.93",
        NSFont.systemFontOfSize_(DesignTokens.TEXT_XS),
        DesignTokens.TEXT_PRIMARY
    )
    metrics_labels['usage_cost'] = usage_cost
    claude_card.addSubview_(usage_cost)

    # [CN] Token 历史折线图
    try:
        from aigard.popover.chart_view import LineChartView
        from Foundation import NSMakeRect
        chart_frame = NSMakeRect(
            DesignTokens.SPACE_3,
            DesignTokens.SPACE_3 + 20,
            card_w - DesignTokens.SPACE_3 * 2,
            50
        )
        # [CN] print(f"创建折线图: frame={chart_frame}")
        # TODO: Translate this log message
        chart_view = LineChartView.alloc().initWithFrame_(chart_frame)
        # [CN] print(f"折线图创建成功: {chart_view}")
        # TODO: Translate this log message
        metrics_labels['token_chart'] = chart_view
        claude_card.addSubview_(chart_view)
        # [CN] print(f"折线图已添加到卡片")
        # TODO: Translate this log message
    except Exception as e:
        # [CN] print(f"❌ 折线图创建失败: {e}")
        # TODO: Translate this log message
        import traceback
        traceback.print_exc()

    # [CN] 请求次数
    usage_requests = _label(
        ((DesignTokens.SPACE_3, DesignTokens.SPACE_2), (card_w - DesignTokens.SPACE_3 * 2, 14)),
        "请求: 0 次",
        NSFont.systemFontOfSize_(DesignTokens.TEXT_XS),
        DesignTokens.TEXT_TERTIARY
    )
    metrics_labels['usage_requests'] = usage_requests
    claude_card.addSubview_(usage_requests)

    y -= claude_card_h + GAP

    # [CN] ── 5. 按钮 ──
    btn_w = (W - 2 * PAD - 2 * GAP) / 3.0
    btn_h = 36.0

    kill_btn = NSButton.alloc().initWithFrame_(((PAD, y - btn_h), (btn_w, btn_h)))
    kill_btn.setTitle_("一键终止")
    kill_btn.setBezelStyle_(1)
    kill_btn.setFont_(NSFont.systemFontOfSize_(DesignTokens.TEXT_SM))
    kill_btn.setTarget_(controller)
    kill_btn.setAction_("killSafeProcesses:")
    blur_view.addSubview_(kill_btn)

    auto_btn = NSButton.alloc().initWithFrame_(((PAD + btn_w + GAP, y - btn_h), (btn_w, btn_h)))
    auto_btn.setTitle_("自动: 关")
    auto_btn.setBezelStyle_(1)
    auto_btn.setFont_(NSFont.systemFontOfSize_(DesignTokens.TEXT_SM))
    auto_btn.setTarget_(controller)
    auto_btn.setAction_("toggleAutokill:")
    metrics_labels['autokill_btn'] = auto_btn
    blur_view.addSubview_(auto_btn)

    panel_btn = NSButton.alloc().initWithFrame_(((PAD + 2 * (btn_w + GAP), y - btn_h), (btn_w, btn_h)))
    panel_btn.setTitle_("面板")
    panel_btn.setBezelStyle_(1)
    panel_btn.setFont_(NSFont.systemFontOfSize_(DesignTokens.TEXT_SM))
    panel_btn.setTarget_(controller)
    panel_btn.setAction_("openDashboard:")
    blur_view.addSubview_(panel_btn)

    return metrics_labels, progress_bars
