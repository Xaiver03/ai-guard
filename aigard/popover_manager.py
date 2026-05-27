"""
原生 Popover 管理器 - 毛玻璃效果的系统监控面板
"""
import objc
from AppKit import (
    NSView, NSPopover, NSViewController,
    NSVisualEffectView, NSVisualEffectBlendingModeBehindWindow,
    NSVisualEffectMaterialPopover,
    NSColor, NSFont, NSTextField, NSButton,
    NSMakeRect, NSMakeSize,
    NSLayoutConstraint, NSLayoutAttributeTop, NSLayoutAttributeBottom,
    NSLayoutAttributeLeading, NSLayoutAttributeTrailing,
    NSLayoutAttributeWidth, NSLayoutAttributeHeight,
    NSLayoutRelationEqual
)
from WebKit import WKWebView
from Foundation import NSURL, NSURLRequest, NSTimer


class PopoverViewController(NSViewController):
    """Popover 视图控制器"""

    def init(self):
        self = objc.super(PopoverViewController, self).init()
        if self is None:
            return None
        self.webview = None
        self.url = "http://127.0.0.1:8765/popover.html"
        return self

    def loadView(self):
        """创建视图"""
        # 创建毛玻璃背景视图
        effect_view = NSVisualEffectView.alloc().initWithFrame_(
            NSMakeRect(0, 0, 380, 520)
        )
        effect_view.setMaterial_(NSVisualEffectMaterialPopover)
        effect_view.setBlendingMode_(NSVisualEffectBlendingModeBehindWindow)
        effect_view.setState_(1)  # NSVisualEffectStateActive

        # 创建 WebView
        self.webview = WKWebView.alloc().initWithFrame_(
            NSMakeRect(0, 0, 380, 520)
        )
        self.webview.setAutoresizingMask_(18)  # 自动调整大小

        # 设置透明背景
        self.webview.setValue_forKey_(False, "drawsBackground")

        # 加载 URL
        request = NSURLRequest.requestWithURL_(NSURL.URLWithString_(self.url))
        self.webview.loadRequest_(request)

        # 将 WebView 添加到毛玻璃视图
        effect_view.addSubview_(self.webview)

        # 设置为控制器的视图
        self.setView_(effect_view)

    def setUrl_(self, url):
        """设置 URL"""
        self.url = url
        if self.webview:
            request = NSURLRequest.requestWithURL_(NSURL.URLWithString_(url))
            self.webview.loadRequest_(request)

    def reload(self):
        """重新加载"""
        if self.webview:
            self.webview.reload_(None)


class PopoverManager:
    """Popover 管理器（单例）"""

    _instance = None

    @classmethod
    def get_instance(cls, status_item=None):
        """获取单例"""
        if cls._instance is None:
            cls._instance = cls(status_item)
        return cls._instance

    def __init__(self, status_item=None):
        """初始化"""
        self.status_item = status_item
        self.popover = None
        self.view_controller = None
        self.update_timer = None
        self._create_popover()

    def _create_popover(self):
        """创建 Popover"""
        # 创建视图控制器
        self.view_controller = PopoverViewController.alloc().init()

        # 创建 Popover
        self.popover = NSPopover.alloc().init()
        self.popover.setContentViewController_(self.view_controller)
        self.popover.setBehavior_(1)  # NSPopoverBehaviorTransient - 点击外部自动关闭
        self.popover.setContentSize_(NSMakeSize(380, 520))

    def show(self, relative_to_rect, of_view, preferred_edge):
        """显示 Popover"""
        if self.popover and not self.popover.isShown():
            self.popover.showRelativeToRect_ofView_preferredEdge_(
                relative_to_rect,
                of_view,
                preferred_edge
            )
            # 启动定时刷新（每2秒）
            self._start_update_timer()

    def hide(self):
        """隐藏 Popover"""
        if self.popover and self.popover.isShown():
            self.popover.close()
            self._stop_update_timer()

    def toggle(self, relative_to_rect, of_view, preferred_edge):
        """切换显示/隐藏"""
        if self.popover.isShown():
            self.hide()
        else:
            self.show(relative_to_rect, of_view, preferred_edge)

    def reload(self):
        """重新加载内容"""
        if self.view_controller:
            self.view_controller.reload()

    def _start_update_timer(self):
        """启动定时刷新"""
        if self.update_timer is None:
            self.update_timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
                2.0,  # 每2秒刷新
                self,
                "timerFired:",
                None,
                True
            )

    def _stop_update_timer(self):
        """停止定时刷新"""
        if self.update_timer:
            self.update_timer.invalidate()
            self.update_timer = None

    def timerFired_(self, timer):
        """定时器回调 - 刷新数据"""
        if self.view_controller and self.view_controller.webview:
            # 通过 JavaScript 刷新数据
            js_code = "if (window.refreshData) { window.refreshData(); }"
            self.view_controller.webview.evaluateJavaScript_completionHandler_(
                js_code,
                None
            )
