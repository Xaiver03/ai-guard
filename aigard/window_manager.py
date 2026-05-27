"""
原生窗口管理器 - 使用 WebView 显示监控面板
"""
import objc
from AppKit import (
    NSWindow, NSWindowStyleMaskTitled, NSWindowStyleMaskClosable,
    NSWindowStyleMaskMiniaturizable, NSWindowStyleMaskResizable,
    NSBackingStoreBuffered, NSApp
)
from WebKit import WKWebView
from Foundation import NSMakeRect, NSURL, NSURLRequest


class DashboardWindow:
    """监控面板窗口（原生 macOS 窗口 + WebView）"""

    _instance = None  # 单例模式

    @classmethod
    def get_instance(cls, url="http://127.0.0.1:8765"):
        """获取单例窗口"""
        if cls._instance is None:
            cls._instance = cls(url)
        return cls._instance

    def __init__(self, url="http://127.0.0.1:8765"):
        """初始化窗口"""
        self.url = url
        self.window = None
        self.webview = None
        self._create_window()

    def _create_window(self):
        """创建原生窗口"""
        # 窗口样式：标题栏 + 关闭 + 最小化 + 可调整大小
        style_mask = (
            NSWindowStyleMaskTitled |
            NSWindowStyleMaskClosable |
            NSWindowStyleMaskMiniaturizable |
            NSWindowStyleMaskResizable
        )

        # 窗口尺寸和位置（居中显示）
        window_rect = NSMakeRect(0, 0, 1200, 800)

        # 创建窗口
        self.window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            window_rect,
            style_mask,
            NSBackingStoreBuffered,
            False
        )

        # 窗口属性
        self.window.setTitle_("AI Guard - 监控面板")
        self.window.center()  # 居中显示
        self.window.setMinSize_((800, 600))  # 最小尺寸

        # 创建 WebView
        webview_rect = NSMakeRect(0, 0, 1200, 800)
        self.webview = WKWebView.alloc().initWithFrame_(webview_rect)
        self.webview.setAutoresizingMask_(18)  # NSViewWidthSizable | NSViewHeightSizable

        # 加载 URL
        request = NSURLRequest.requestWithURL_(NSURL.URLWithString_(self.url))
        self.webview.loadRequest_(request)

        # 将 WebView 添加到窗口
        self.window.setContentView_(self.webview)

    def show(self):
        """显示窗口"""
        if self.window:
            self.window.makeKeyAndOrderFront_(None)
            NSApp.activateIgnoringOtherApps_(True)  # 激活应用

    def hide(self):
        """隐藏窗口"""
        if self.window:
            self.window.orderOut_(None)

    def toggle(self):
        """切换窗口显示/隐藏"""
        if self.window and self.window.isVisible():
            self.hide()
        else:
            self.show()

    def reload(self):
        """重新加载页面"""
        if self.webview:
            self.webview.reload_(None)

    def load_url(self, url):
        """加载新 URL"""
        if self.webview:
            request = NSURLRequest.requestWithURL_(NSURL.URLWithString_(url))
            self.webview.loadRequest_(request)
