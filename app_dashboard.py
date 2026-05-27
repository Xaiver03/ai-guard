"""app_dashboard.py — 独立的监控面板应用

这是一个独立的 macOS 应用,显示 AI Guard 的监控面板。
可以独立运行,也可以从主应用启动。
"""

import os
import sys
from pathlib import Path

import objc
from Foundation import NSObject, NSURL, NSURLRequest, NSMakeRect
from AppKit import (
    NSApplication, NSWindow, NSWindowStyleMaskTitled, NSWindowStyleMaskClosable,
    NSWindowStyleMaskMiniaturizable, NSWindowStyleMaskResizable,
    NSBackingStoreBuffered, NSApp
)
from WebKit import WKWebView


class DashboardAppDelegate(NSObject):
    """监控面板应用委托"""

    def init(self):
        self = objc.super(DashboardAppDelegate, self).init()
        if self is None:
            return None

        # 服务地址
        self.url = "http://127.0.0.1:8765"

        # 创建窗口
        self._create_window()

        return self

    def _create_window(self):
        """创建主窗口"""
        # 窗口样式 - 添加全屏支持
        style_mask = (
            NSWindowStyleMaskTitled |
            NSWindowStyleMaskClosable |
            NSWindowStyleMaskMiniaturizable |
            NSWindowStyleMaskResizable |
            (1 << 14)  # NSWindowStyleMaskFullScreen
        )

        # 窗口尺寸和位置
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
        self.window.center()
        self.window.setMinSize_((800, 600))

        # 允许全屏
        self.window.setCollectionBehavior_(1 << 7)  # NSWindowCollectionBehaviorFullScreenPrimary

        # 创建 WebView
        webview_rect = NSMakeRect(0, 0, 1200, 800)
        self.webview = WKWebView.alloc().initWithFrame_(webview_rect)
        self.webview.setAutoresizingMask_(18)  # 自动调整大小

        # 加载 URL
        request = NSURLRequest.requestWithURL_(NSURL.URLWithString_(self.url))
        self.webview.loadRequest_(request)

        # 将 WebView 添加到窗口
        self.window.setContentView_(self.webview)

        # 显示窗口
        self.window.makeKeyAndOrderFront_(None)

    def applicationDidFinishLaunching_(self, notification):
        """应用启动完成"""
        NSApp.activateIgnoringOtherApps_(True)

    def applicationShouldTerminateAfterLastWindowClosed_(self, sender):
        """关闭最后一个窗口时不退出应用,保持在后台"""
        return False


def main():
    """主函数"""
    app = NSApplication.sharedApplication()
    delegate = DashboardAppDelegate.alloc().init()
    app.setDelegate_(delegate)
    app.run()


if __name__ == "__main__":
    main()
