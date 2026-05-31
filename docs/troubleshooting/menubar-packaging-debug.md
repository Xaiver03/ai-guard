# 菜单栏图标不显示 — 排查记录（2026-05-31 傍晚）

## 当前状态

**症状：** 打包后的 .app 进程正常、API 正常、日志正常，但菜单栏完全看不到任何图标或文字。

## 关键发现（16:30）

**测试结果对照表：**

| 脚本 | 结构 | 打包后显示 | 说明 |
|------|------|-----------|------|
| bar_test3.py | 状态栏在 module-level 创建，无 delegate | ✅ TEST3 | |
| bar_direct.py | 同上，有 setActivationPolicy + delegate | ✅ DIREC | |
| bar_test4.py | delegate init() 创建状态栏，无 NSTimer，无 imports | ✅ TEST4 | |
| bar_test5.py | 同上 + delegate didFinishLaunching | ✅ TEST5 | |
| bar_test7.py | bar_test4 完整结构 + 所有 app_native imports + NSTimer + Popover/DashboardWindow | ❌ 不显示 | **关键差异在 imports** |
| app_native.py | 同 bar_test7 | ❌ 不显示 | 同 bar_test7 |

**关键发现：**
- 无 imports 时（bar_test3-5）：✅ 显示
- 有完整 imports 时（bar_test7, app_native）：❌ 不显示
- 日志完全正常，状态栏项创建成功，run() 被调用

**进一步测试方向：**
1. `bar_test3.py` + 逐个加上 app_native 的 imports，找出哪个 import 导致问题
2. 检查 py2app 打包后 sys.modules 中是否有冲突的模块覆盖了 PyObjC 的 NSStatusBar
3. 考虑是 WebKit 的 WKWebView 导入导致 NSStatusBar 被替换

## 排查进展

### 已排除的原因

| 测试 | 结果 | 说明 |
|------|------|------|
| 完整 app_native.py（日志完整）| ❌ 不显示 | 日志一切正常，状态栏项创建成功 |
| 最小化脚本（仅 NSStatusBar，无依赖）| ❌ 不显示 | 纯 PyObjC，30行代码，仍不显示 |

**结论：问题不在 Python 代码逻辑。在打包配置（py2app 模板或 Info.plist）。**

### 打包环境关键信息

**Info.plist（当前）：**
```xml
<key>NSMainNibFile</key>
<string></string>
<key>NSPrincipalClass</key>
<string>NSApplication</string>
<key>PyMainFileNames</key>
<array><string>__boot__</string></array>
```

**py2app 模板：** `app`（非 `bundle`）

**Resources 目录：** 无 `.nib` 文件，无 `MainMenu.nib`

### 最小化测试脚本（/tmp/mini_bar.py）

```python
"""Ultra-minimal status bar test for packaged app"""
import os, sys, io
os.environ['PYTHONIOENCODING'] = 'utf-8'
log = open('/tmp/mini_test.log', 'wb', 0)
sys.stdout = io.TextIOWrapper(log, encoding='utf-8', line_buffering=True, write_through=True, errors='replace')
sys.stderr = sys.stdout
print("mini_test started")

from AppKit import NSApplication, NSStatusBar, NSVariableStatusItemLength, NSMenu, NSMenuItem
from Foundation import NSObject
import objc

class Mini(NSObject):
    def init(self):
        self = objc.super(Mini, self).init()
        print("init")
        si = NSStatusBar.systemStatusBar().statusItemWithLength_(NSVariableStatusItemLength)
        si.setVisible_(True)
        btn = si.button()
        if btn:
            btn.setTitle_("MINI")
        m = NSMenu.alloc().init()
        it = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Quit", "terminate:", "q")
        from AppKit import NSApp
        it.setTarget_(NSApp)
        m.addItem_(it)
        si.setMenu_(m)
        print("done, menu visible")
        return self

app = NSApplication.sharedApplication()
d = Mini.alloc().init()
app.setDelegate_(d)
app.run()
```

日志输出（确认运行正常）：
```
mini_test started
init
done, menu visible
```

但菜单栏完全不显示。

---

## 待测试方向

### 方向 1：py2app 模板改为 `bundle`

py2app 有两个模板：
- `app`（默认）：完整 App，包含 AppKit 主循环
- `bundle`：最小化 bundle，可能影响 UI 初始化

setup.py 中尝试添加：
```python
"template": "bundle",
```

### 方向 2：添加 `NSApplicationActivationPolicy`

在 Python 代码中设置激活策略（`app.setActivationPolicy_`），而不是依赖 Info.plist：
```python
from AppKit import NSApplication, NSApplicationActivationPolicyAccessory
app = NSApplication.sharedApplication()
app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
```

### 方向 3：创建最小化 nib 文件

py2app 的 `app` 模板可能要求必须有 MainMenu.xib/nib。尝试手动创建一个最小化的 nib。

### 方向 4：对比能工作的历史版本打包配置

之前能显示时（commit 4762a2a 或更早）的打包配置是怎样的？检查：
- py2app template 设置
- Info.plist 中的 NSMainNibFile 值（当时是否有 nib 文件）
- 是否有 `LSUIElement` 设置
- `NSPrincipalClass` 设置

### 方向 5：开发模式 vs 打包后关键差异

| 项目 | 开发模式（`python app_native.py`） | 打包后 |
|------|----------------------------------|--------|
| `sys.executable` | `/path/to/venv/bin/python` | `/path/to/AI Guard.app/Contents/MacOS/AI Guard` |
| `sys.frozen` | `False` 或不存在 | `True` |
| `NSApp` 创建方式 | 相同 | 相同 |
| 状态栏项创建 | 相同 | 相同（日志确认） |

**关键：开发模式用 `python app_native.py` 能显示，打包后不能。差异在于 py2app 的启动方式和模板。**

---

## 下一步操作

1. 先尝试方向 2（在 Python 中显式设置 activationPolicy）
2. 尝试方向 1（改 template 为 bundle）
3. 如果都不行，尝试创建一个最小化的 MainMenu.xib

## 历史参考

- **2026-05-31 傍晚**：重写 app_native.py，修复 killSafe 自保护，同时发现菜单栏问题
- 之前多次修复：rumps vs PyObjC、`setMenu_` vs `setAction_`、`setVisible_` 调用时机、中文注释 ASCII 错误等
- **b65468d 实际上不工作**：那个版本打包后会 UnicodeEncodeError 崩溃
- **97875fc** 改用 `setAction_`，引入打包后不显示问题（已修复）
- **当前问题**：连纯 PyObjC 最小化脚本都不显示，问题在 py2app 模板层面