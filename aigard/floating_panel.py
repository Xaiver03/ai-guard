"""
浮动面板 - 可移动、可全屏的独立窗口
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
    """浮动面板 - 替代 Popover"""

    _instance = None

    @classmethod
    def get_instance(cls, controller):
        """获取单例"""
        if cls._instance is None:
            cls._instance = cls(controller)
        return cls._instance

    def __init__(self, controller):
        """初始化浮动面板"""
        self.controller = controller

        # 创建窗口
        style_mask = (
            NSWindowStyleMaskTitled |
            NSWindowStyleMaskClosable |
            NSWindowStyleMaskMiniaturizable |
            NSWindowStyleMaskResizable |
            NSWindowStyleMaskUtilityWindow
        )

        # 窗口位置和大小
        frame = NSMakeRect(0, 0, 360, 500)

        self.panel = NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            frame,
            style_mask,
            NSBackingStoreBuffered,
            False
        )

        # 设置窗口属性
        self.panel.setTitle_("AI Guard")
        self.panel.setLevel_(NSFloatingWindowLevel)  # 浮动在其他窗口之上
        self.panel.setCollectionBehavior_(1 << 0)  # NSWindowCollectionBehaviorCanJoinAllSpaces

        # 设置内容视图
        self.panel.setContentView_(controller.view())

    def show(self):
        """显示面板"""
        self.panel.makeKeyAndOrderFront_(None)
        self.panel.center()  # 居中显示

    def hide(self):
        """隐藏面板"""
        self.panel.orderOut_(None)

    def toggle(self):
        """切换显示/隐藏"""
        if self.panel.isVisible():
            self.hide()
        else:
            self.show()

    def is_visible(self):
        """是否可见"""
        return self.panel.isVisible()
