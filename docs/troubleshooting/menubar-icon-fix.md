# 菜单栏图标不显示问题修复记录

## 问题描述

**症状：**
- 应用进程正常运行（`ps aux` 可见）
- API 正常响应（`curl http://localhost:8765/api/metrics` 返回数据）
- 日志显示状态刷新方法正常调用
- **但菜单栏右上角看不到任何图标或文字**

## 问题根源

通过 Git 版本对比（`git diff b65468d HEAD`）定位到问题：

**commit 4762a2a** 将 `setup.py` 中的入口文件从 `app_native.py` 改为 `app_menubar.py`

### 两种实现的区别

| 实现方式 | 框架 | 状态 |
|---------|------|------|
| `app_native.py` | 纯 PyObjC，直接操作 NSStatusBar API | ✅ 正常显示 |
| `app_menubar.py` | rumps 框架封装 | ❌ 无法显示图标 |

### 为什么 rumps 实现失败？

尝试过的修复方案均无效：
- ❌ 禁用 `LSUIElement` 配置
- ❌ 修改 rumps 初始化参数（name, title）
- ❌ 延迟创建 DashboardWindow
- ❌ 重启 SystemUIServer 清除缓存

**结论：** rumps 框架在当前 py2app 打包配置下无法正常创建可见的 NSStatusItem

## 修复方案

### 1. 修改 setup.py 入口文件

```python
# 从
APP = ["app_menubar.py"]

# 改回
APP = ["app_native.py"]
```

### 2. 移植新功能到 app_native.py

从 `app_menubar.py` 提取以下功能：

#### 新增方法

```python
def openTools_(self, sender):
    """打开 AI 工具导航（原生窗口）"""
    self.dashboard_window.load_url(f"{self.url}/tools.html")
    self.dashboard_window.show()

def openPractices_(self, sender):
    """打开最佳实践（原生窗口）"""
    self.dashboard_window.load_url(f"{self.url}/practices.html")
    self.dashboard_window.show()
```

#### 新增菜单项

在 `_build_menu()` 方法中添加：

```python
# AI 工具导航
item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
    "AI 工具导航", "openTools:", ""
)
item.setTarget_(self)
self.menu.addItem_(item)

# 最佳实践
item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
    "最佳实践", "openPractices:", ""
)
item.setTarget_(self)
self.menu.addItem_(item)
```

### 3. 重新打包安装

```bash
python setup.py py2app
sudo rm -rf /Applications/AI\ Guard.app
sudo cp -R dist/AI\ Guard.app /Applications/
```

## 验证结果

✅ 菜单栏图标正常显示  
✅ 所有新功能（AI 工具导航、最佳实践）正常工作  
✅ 原有功能（仪表盘、偏好设置、关于）正常工作

## 重要原则

**永远不要归咎于系统问题！**

如果之前能显示，现在不显示，一定是代码改动导致的。常见的错误归因：
- ❌ "菜单栏空间不足"
- ❌ "图标被系统隐藏"
- ❌ "macOS 缓存问题"

**正确的排查思路：**
1. 使用 `git log` 查看最近的提交
2. 使用 `git diff <last-working-commit> HEAD` 对比代码变更
3. 定位到具体的代码改动
4. 理解改动的影响
5. 针对性修复

## 相关 Commit

- **b65468d**: 修复窗口移动和通知显示问题（最后能工作的版本）
- **4762a2a**: 启用 LSUIElement 并移除代码中的激活策略设置（引入问题）
- **当前修复**: 将入口改回 app_native.py 并移植新功能

## 技术总结

### PyObjC vs rumps

| 特性 | PyObjC | rumps |
|------|--------|-------|
| 学习曲线 | 陡峭 | 平缓 |
| 灵活性 | 高 | 中 |
| 稳定性 | 高（直接调用系统 API） | 中（依赖框架封装） |
| 打包兼容性 | 好 | 可能有问题 |

**建议：** 对于 macOS 菜单栏应用，优先使用纯 PyObjC 实现，避免依赖第三方框架。

## 未来改进

- [ ] 考虑完全移除 `app_menubar.py`，避免混淆
- [ ] 在 CI/CD 中添加菜单栏图标显示的自动化测试
- [ ] 文档化 PyObjC 菜单栏开发的最佳实践
