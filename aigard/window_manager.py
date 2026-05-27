"""
原生窗口管理器 - 使用 WebView 显示监控面板
"""
import objc
from AppKit import (
    NSWindow, NSWindowStyleMaskTitled, NSWindowStyleMaskClosable,
    NSWindowStyleMaskMiniaturizable, NSWindowStyleMaskResizable,
    NSBackingStoreBuffered, NSApp
)
from WebKit import WKWebView, WKWebViewConfiguration, WKPreferences
from Foundation import NSMakeRect, NSURL, NSURLRequest


class DashboardWindow:
    """监控面板窗口(原生 macOS 窗口 + WebView)"""

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
        # 窗口样式:标题栏 + 关闭 + 最小化 + 可调整大小 + 全屏
        style_mask = (
            NSWindowStyleMaskTitled |
            NSWindowStyleMaskClosable |
            NSWindowStyleMaskMiniaturizable |
            NSWindowStyleMaskResizable |
            (1 << 14)  # NSWindowStyleMaskFullScreen
        )

        # 窗口尺寸和位置(居中显示)
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

        # 允许全屏 - 使用正确的常量
        self.window.setCollectionBehavior_(128)  # NSWindowCollectionBehaviorFullScreenPrimary = 1 << 7 = 128

        # 配置 WebView - 启用 JavaScript 和本地存储
        config = WKWebViewConfiguration.alloc().init()
        preferences = WKPreferences.alloc().init()
        preferences.setJavaScriptEnabled_(True)
        preferences.setJavaScriptCanOpenWindowsAutomatically_(True)
        config.setPreferences_(preferences)

        # 启用开发者工具(调试用)
        config.preferences().setValue_forKey_(True, "developerExtrasEnabled")

        # 允许跨域请求(localhost)
        try:
            config.setValue_forKey_(True, "allowUniversalAccessFromFileURLs")
        except:
            pass

        # 创建 WebView
        webview_rect = NSMakeRect(0, 0, 1200, 800)
        self.webview = WKWebView.alloc().initWithFrame_configuration_(webview_rect, config)
        self.webview.setAutoresizingMask_(18)  # NSViewWidthSizable | NSViewHeightSizable

        # 允许滚动
        try:
            self.webview.enclosingScrollView().setHasVerticalScroller_(True)
            self.webview.enclosingScrollView().setHasHorizontalScroller_(False)
        except:
            pass

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
