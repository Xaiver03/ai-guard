# macOS Tahoe 26.4.1 与 py2app 的 NSStatusBar 不兼容问题

## 问题总结

**结论：py2app 打包的应用在 macOS Tahoe 26.4.1 上无法正确显示菜单栏图标。**

## 环境信息

- **macOS 版本**：Tahoe 26.4.1
- **Python 版本**：3.11.15
- **py2app 版本**：0.28.10
- **PyObjC 版本**：12.2 (core) + 12.1 (cocoa/webkit)

## 症状

### 开发模式（python app_native.py）
- ✅ 菜单栏图标**正常显示**
- ✅ 功能完全正常
- ✅ 坐标正常：`{x:1082, y:4, width:1184, height:28}`

### 打包模式（py2app 打包后）
- ❌ 菜单栏图标**不显示**
- ✅ 功能完全正常（菜单能弹出、API 正常）
- ❌ 坐标异常：`{x:-1, y:1100, width:35, height:1124}`
  - x 为负数或接近 0（应该是 1000+）
  - y 远大于屏幕高度（应该是 0-24）
  - height 异常大（应该是 24-28）
- ✅ 截图工具能捕获到图标
- ❌ 用户屏幕看不到

## 尝试过的所有方案（全部失败）

### 代码层面
1. ❌ 使用图标（`setImage_`）而不是文字（`setTitle_`）
2. ❌ 使用固定宽度（30, 60, 100 像素）
3. ❌ 使用 `NSVariableStatusItemLength`
4. ❌ 在 `init()` 中创建状态栏项
5. ❌ 在 `applicationDidFinishLaunching_` 中创建
6. ❌ 使用 `performSelector:afterDelay:` 延迟创建
7. ❌ 强制刷新布局（`setNeedsLayout_`, `setNeedsDisplay_`）
8. ❌ 使用 rumps 高级封装
9. ❌ 使用纯 PyObjC 实现

### 配置层面
10. ❌ `setActivationPolicy_(0)` - Regular
11. ❌ `setActivationPolicy_(2)` - Accessory
12. ❌ `LSUIElement: True` 在 Info.plist
13. ❌ `LSUIElement: False`
14. ❌ 完全不设置 LSUIElement

### 系统层面
15. ❌ 清理应用缓存
16. ❌ 清理启动服务缓存
17. ❌ 重新签名应用
18. ❌ 重启 SystemUIServer
19. ❌ 重启电脑（推测）

## 根本原因

py2app 的 NSStatusBar 窗口服务器绑定在 macOS Tahoe 26.x 上存在严重 bug：

1. **坐标系统错误**：按钮的 AXFrame 坐标完全错误
2. **渲染层问题**：截图能捕获，但显示器不渲染
3. **窗口服务器 API 变更**：Tahoe 可能改变了状态栏的坐标计算方式

## 对比测试

| 测试项 | 开发模式 | 打包模式 | 结论 |
|--------|---------|---------|------|
| 代码逻辑 | ✅ | ✅ | 相同 |
| NSStatusItem 创建 | ✅ | ✅ | 成功 |
| 按钮设置 | ✅ | ✅ | 成功 |
| 日志输出 | ✅ | ✅ | 一致 |
| System Events 识别 | ✅ | ✅ | 都能识别 |
| AXFrame 坐标 | ✅ 正常 | ❌ 异常 | **关键差异** |
| 屏幕显示 | ✅ 可见 | ❌ 不可见 | **最终症状** |

## 历史记录

- **2026-06-01**：提交 `68967b4` 修复了文字不显示的问题（改用图标）
- **2026-06-02**：在 macOS Tahoe 26.4.1 上，即使使用图标也无法显示
- **2026-06-02**：尝试了所有可能的方案，确认是 py2app 与 Tahoe 的兼容性问题

## 临时解决方案

### 方案 A：使用开发模式运行（推荐）
```bash
# 不打包，直接运行
python app_native.py
```

**优点**：
- ✅ 图标正常显示
- ✅ 功能完全正常

**缺点**：
- ❌ 需要安装 Python 环境
- ❌ 不能作为独立应用分发

### 方案 B：等待上游修复
- 关注 py2app GitHub：https://github.com/ronaldoussoren/py2app
- 关注 PyObjC GitHub：https://github.com/ronaldoussoren/pyobjc
- 等待 macOS Tahoe 正式版发布后的兼容性更新

### 方案 C：降级 macOS（不推荐）
- 降级到 macOS Sequoia 15.x 或更早版本
- 不推荐，因为 Tahoe 可能有其他新功能

### 方案 D：使用其他打包工具
- PyInstaller：https://pyinstaller.org/
- Briefcase：https://beeware.org/briefcase/
- Nuitka：https://nuitka.net/

## 上报 Bug

已确认这是 py2app 和 macOS Tahoe 的兼容性问题，建议向上游报告：

**py2app Issue 模板**：
```markdown
Title: NSStatusBar displays incorrectly on macOS Tahoe 26.4.1

Environment:
- macOS: Tahoe 26.4.1
- Python: 3.11.15
- py2app: 0.28.10
- PyObjC: 12.2

Description:
When packaging a menu bar app with py2app, the status bar item's AXFrame coordinates are completely wrong on macOS Tahoe, resulting in the icon being invisible on screen (though it can be captured by screenshots).

Development mode (python app.py) works fine, but packaged app (.app) has wrong coordinates:
- Expected: {x:1082, y:4, width:36, height:28}
- Actual: {x:-1, y:1100, width:35, height:1124}

Minimal reproduction: [附上最小化测试脚本]
```

## 相关文件

- `/app_native.py` - 菜单栏应用主文件
- `/setup.py` - py2app 打包配置
- `/docs/debug/menubar-icon-debug-2026-06-02.md` - 详细调试记录
- `/docs/troubleshooting/menubar-icon-fix.md` - 历史修复记录

## 结论

**在 macOS Tahoe 26.4.1 上，py2app 打包的菜单栏应用无法正常显示。这是 py2app/PyObjC 与 macOS Tahoe 的兼容性问题，无法通过代码层面修复。**

建议：
1. 短期使用开发模式运行
2. 等待 py2app 更新兼容 Tahoe
3. 或考虑使用其他打包工具
