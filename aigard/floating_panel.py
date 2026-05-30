"""
# [CN] 浮动面板 - 可移动、可全屏的独立窗口
"""
import objc
from AppKit import (
    NSPanel, NSWindowStyleMaskTitled, NSWindowStyleMaskClosable,
    NSWindowStyleMaskMiniaturizable, NSWindowStyleMaskResizable,
    NSWindowStyleMaskUtilityWindow, NSWindowStyleMaskNonactivatingPanel,
    NSBackingStoreBuffered, NSFloatingWindowLevel
)
from Foundation import NSRect, NSMakeRect


class FloatingPanel:
    # [CN] """浮动面板 - 替代 Popover"""

    _instance = None

    @classmethod
    def get_instance(cls, controller):
        # [CN] """获取单例"""
        if cls._instance is None:
            cls._instance = cls(controller)
        return cls._instance

    def __init__(self, controller):
        # [CN] """初始化浮动面板"""
        self.controller = controller

        # [CN] # 创建窗口
        style_mask = (
            NSWindowStyleMaskTitled |
            NSWindowStyleMaskClosable |
            NSWindowStyleMaskMiniaturizable |
            NSWindowStyleMaskResizable |
            NSWindowStyleMaskUtilityWindow
        )

        # [CN] # 窗口位置和大小
        frame = NSMakeRect(0, 0, 360, 500)

        self.panel = NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            frame,
            style_mask,
            NSBackingStoreBuffered,
            False
        )

        # [CN] # 设置窗口属性
        self.panel.setTitle_("AI Guard")
        # [CN] self.panel.setLevel_(NSFloatingWindowLevel)  # 浮动在其他窗口之上
        self.panel.setCollectionBehavior_(1 << 0)  # NSWindowCollectionBehaviorCanJoinAllSpaces

        # [CN] # 设置内容视图
        self.panel.setContentView_(controller.view())

    def show(self):
        # [CN] """显示面板"""
        self.panel.makeKeyAndOrderFront_(None)
        self.panel.center()  # [CN] 居中显示

    def hide(self):
        # [CN] """隐藏面板"""
        self.panel.orderOut_(None)

    def toggle(self):
        # [CN] """切换显示/隐藏"""
        if self.panel.isVisible():
            self.hide()
        else:
            self.show()

    def is_visible(self):
        """YesNoVisible"""
        return self.panel.isVisible()
