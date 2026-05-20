"""setup.py — py2app 打包配置

用法：
    python setup.py py2app --alias   # 开发模式（快速，引用本地包）
    python setup.py py2app           # 正式打包（独立 .app，可分发）
    bash build.sh                    # 一键正式打包
"""
from setuptools import setup

APP = ["app_menubar.py"]

DATA_FILES = [
    ("aigard/ui",    ["aigard/ui/index.html"]),
    ("",             ["config.toml"]),
    ("assets",       ["assets/icon.icns"]),
]

OPTIONS = {
    "argv_emulation": False,   # rumps App 不需要 argv emulation
    "iconfile":       "assets/icon.icns",
    "plist": {
        # App 身份
        "CFBundleName":               "AI Guard",
        "CFBundleDisplayName":        "AI Guard",
        "CFBundleIdentifier":         "com.aigard.menubar",
        "CFBundleVersion":            "1.1.2",
        "CFBundleShortVersionString": "1.1.2",
        # 只在菜单栏显示，不出现在 Dock
        "LSUIElement":                True,
        "NSHighResolutionCapable":    True,
        # 权限声明（macOS Ventura+ 需要）
        "NSUserNotificationUsageDescription":
            "AI Guard 在内存/Swap/磁盘超过告警阈值时发送通知提醒。",
        "NSLocalNetworkUsageDescription":
            "AI Guard 在本地端口 8765 启动监控服务，仅供本机使用，不访问外部网络。",
    },
    "packages": [
        "aigard",
        "aigard.core",
        "aigard.api",
        "fastapi",
        "uvicorn",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.websockets",
        "uvicorn.lifespan",
        "psutil",
        "rumps",
        "starlette",
        "starlette.middleware",
        "anyio",
        "anyio._backends",
        "pydantic",
        "pydantic_core",
        "tomli",
        "tomli_w",
        "sniffio",
        "h11",
        "click",
        "pkg_resources",
        "pkg_resources._vendor",
        "pkg_resources.extern",
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
        "httpx",
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
