"""setup.py — py2app 打包配置

用法：
    python setup.py py2app --alias   # 开发模式（快速，引用本地包）
    python setup.py py2app           # 正式打包（独立 .app，可分发）
    bash build.sh                    # 一键正式打包
"""
from setuptools import setup

APP = ["app_native.py"]

DATA_FILES = [
    ("aigard/ui",    ["aigard/ui/index.html",
                      "aigard/ui/bookmarks.html",
                      "aigard/ui/usage.html",
                      "aigard/ui/tools.html",
                      "aigard/ui/practices.html",
                      "aigard/ui/settings.html",
                      "aigard/ui/about.html"]),
    ("aigard/ui/css", ["aigard/ui/css/design-system.css",
                       "aigard/ui/css/components.css",
                       "aigard/ui/css/usage.css",
                       "aigard/ui/css/bookmarks.css"]),
    ("aigard/ui/js",  ["aigard/ui/js/usage-i18n.js",
                       "aigard/ui/js/usage-data.js",
                       "aigard/ui/js/usage-charts.js",
                       "aigard/ui/js/usage-pricing.js",
                       "aigard/ui/js/usage-icons.js"]),
    ("aigard/data",  ["aigard/data/tools.json",
                      "aigard/data/practices.json"]),
    ("",             ["config.toml", "main.py", "alert_history.py"]),
    ("assets",       ["assets/icon.icns", "assets/menubar_icon.png", "assets/menubar_icon_color.png"]),
]

OPTIONS = {
    "argv_emulation": False,   # 原生 App 不需要 argv emulation
    "iconfile":       "assets/icon.icns",
    "optimize":       0,       # 禁用字节码优化，避免 mypyc 依赖问题
    "semi_standalone": False,  # 完全独立模式
    "site_packages":   False,  # 不包含整个 site-packages
    "compressed":      False,  # 不压缩，便于调试
    "plist": {
        # App 身份
        "CFBundleName":               "AI Guard",
        "CFBundleDisplayName":        "AI Guard",
        "CFBundleIdentifier":         "com.xaiver.aiguard",
        "CFBundleVersion":            "1.1.3",
        "CFBundleShortVersionString": "1.1.3",
        "NSHighResolutionCapable":    True,
        "NSMainNibFile":               "",
        # 权限声明（macOS Ventura+ 需要）
        "NSUserNotificationUsageDescription":
            "AI Guard 在内存/Swap/磁盘超过告警阈值时发送通知提醒。",
        "NSLocalNetworkUsageDescription":
            "AI Guard 在本地端口 8765 启动监控服务，仅供本机使用，不访问外部网络。",
    },
    "packages": [
        "aigard",
        "aigard.core",
        "aigard.core.usage",
        "aigard.api",
        "aigard.bookmarks",
        "aigard.popover",
        "rumps",
        "fastapi",
        "hypercorn",
        "psutil",
        "starlette",
        "anyio",
        "pydantic",
        "pydantic_core",
        "tomli",
        "tomli_w",
        "sniffio",
        "h11",
        "h2",
        "hpack",
        "hyperframe",
        "wsproto",
        "priority",
        "pkg_resources",
        "requests",
        "packaging",
        "httpx",
        "httpcore",
        "WebKit",
        "objc",
    ],
    "includes": [
        "PyObjCTools.AppHelper",
        "hypercorn.asyncio",
        "hypercorn.config",
        "hypercorn.protocol.h11",
        "hypercorn.protocol.h2",
        "hypercorn.protocol.ws_stream",
        "anyio._backends._asyncio",
    ],
    "excludes": [
        "tkinter",
        "unittest",
        "pydoc",
        "doctest",
        "numpy",
        "Cython",
        "scipy",
        "pandas",
        "matplotlib",
        "PIL",
        "cv2",
        "torch",
        "tensorflow",
        "pytz",
        "websockets",
        "cffi",
        "cryptography",
        "dns",
        "aiofiles",
        "multipart",
        "jinja2",
        "itsdangerous",
        "pkg_resources._vendor.jaraco",
        "pkg_resources.extern",
    ],
    # 不启用沙盒（未上 App Store，沙盒会阻止 psutil 扫描进程）
    "no_strip": False,
}

setup(
    app=APP,
    name="AI Guard",
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
