# 菜单栏图标不显示问题调试记录

日期：2026-06-02

## 问题描述

- **开发模式**（`python app_native.py`）：菜单栏图标**能显示** ✅
- **打包模式**（`py2app` 打包后）：菜单栏图标**不显示** ❌
- 功能完全正常：菜单能弹出、API 正常、日志正常
- 截图工具能捕获到图标，但用户屏幕看不到

## 关键发现

### 1. 坐标异常（已确认）

**开发模式菜单栏项坐标：**
```
AXFrame: {x:1082, y:4, width:1184, height:28}
Title: ██████
```

**打包模式菜单栏项坐标：**
```
AXFrame: {x:7, y:1111, width:109, height:1135}
Title: ██████
```

**结论：** 打包版本的按钮**几何属性完全错误**，导致渲染在错误的位置或尺寸异常。

### 2. NSStatusBar 初始化问题

在 `init()` 方法中创建 `NSStatusItem` 可能在 py2app 打包后的运行时环境中出现问题：
- 窗口服务器可能还未完全初始化
- PyObjC 的 Cocoa 绑定可能在打包后的时序不同

### 3. LSUIElement 的影响

- `LSUIElement: True`：应用变成纯后台，`menu bar` 数量为 0
- `LSUIElement: False` + `setActivationPolicy_(2)`：开发模式正常，打包后坐标异常
- `LSUIElement: False` + `setActivationPolicy_(0)`：Dock 可见，菜单栏图标不可见

## 尝试过的方案

### 方案 1：修改图标和文字
- ❌ 只用文字（`setTitle_`）
- ❌ 只用图标（`setImage_`）
- ❌ 文字+emoji（`🔵 AG`）
- ❌ 超大文字（`AI GUARD`）
- ❌ 方块字符（`██████`）
- ❌ 红色背景+白色文字
- ❌ 生成的彩色方块图标

### 方案 2：修改 Info.plist
- ❌ 添加 `LSUIElement: True`
- ❌ 移除 `LSUIElement`
- ❌ 修改 `NSMainNibFile`

### 方案 3：修改状态栏项创建方式
- ❌ 固定宽度（60, 100像素）
- ❌ `NSVariableStatusItemLength`
- ❌ 延迟创建（`performSelector:afterDelay:`）
- ⏳ 在 `applicationDidFinishLaunching_` 中创建（待测试）

### 方案 4：修改激活策略
- ❌ `setActivationPolicy_(2)` + `LSUIElement: False`
- ❌ `setActivationPolicy_(2)` + `LSUIElement: True`
- ❌ `setActivationPolicy_(0)` + `LSUIElement: False`（当前状态）

### 方案 5：清理缓存和签名
- ❌ 清理应用缓存
- ❌ 重新签名
- ❌ 清理启动服务缓存
- ❌ 重启 SystemUIServer

## 当前状态

- `setActivationPolicy_(0)` （普通应用模式）
- `LSUIElement: False` （不在 Info.plist 中设置）
- Dock 图标：✅ 可见
- 菜单栏图标：❌ 不可见
- 日志显示一切正常

## 下一步计划

### 选项 A：延迟创建状态栏项
在 `applicationDidFinishLaunching_` 中创建 `NSStatusItem`，而不是在 `init()` 中。

### 选项 B：使用 rumps 库
rumps 是 Python 菜单栏应用的高级封装，可能处理了 py2app 的兼容性问题。

### 选项 C：检查 py2app 的启动器代码
py2app 的启动器可能在初始化 NSApplication 时有特殊行为。

### 选项 D：对比二进制和动态库
检查打包后的应用是否缺少必要的 Cocoa 框架绑定。

## 参考资料

- PyObjC 文档：https://pyobjc.readthedocs.io/
- py2app 文档：https://py2app.readthedocs.io/
- NSStatusBar 文档：https://developer.apple.com/documentation/appkit/nsstatusbar
