"""setup_dashboard.py — 监控面板独立应用打包配置

用法：
    python setup_dashboard.py py2app
"""
from setuptools import setup

APP = ["app_dashboard.py"]

DATA_FILES = []

OPTIONS = {
    "argv_emulation": False,
    "iconfile": "assets/icon.icns",
    "plist": {
        "CFBundleName": "AI Guard Dashboard",
        "CFBundleDisplayName": "AI Guard Dashboard",
        "CFBundleIdentifier": "com.xaiver.aiguard.dashboard",
        "CFBundleVersion": "1.1.3",
        "CFBundleShortVersionString": "1.1.3",
        "NSHighResolutionCapable": True,
    },
    "packages": [
        "objc",
    ],
    "includes": [
        "Foundation",
        "AppKit",
    ],
    "excludes": [
        "tkinter",
        "unittest",
        "pydoc",
        "doctest",
        "numpy",
        "scipy",
        "pandas",
        "matplotlib",
        "PIL",
        "torch",
        "tensorflow",
    ],
    "no_strip": False,
    "site_packages": True,
}

setup(
    app=APP,
    name="AI Guard Dashboard",
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
