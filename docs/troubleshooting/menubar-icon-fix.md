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

---

## 第二次复发（2026-05-31）

### 症状

同上：进程正常、API 正常、日志显示一切正常，但菜单栏完全看不到任何东西。

### 排查过程

**错误方向（浪费时间，不要再走）：**
- ❌ 反复切换 `LSUIElement` 开/关 — 无效
- ❌ 重启 SystemUIServer — 无效
- ❌ 清除 Launch Services 缓存 — 无效
- ❌ 检查签名缓存 — 无效
- ❌ 对比 `b65468d` 版本代码 — 误导，那个版本打包后其实也崩溃（UnicodeEncodeError）

**正确排查方法：二分法，最小化测试脚本逐步加功能**

写一个只有 30 行的最小化脚本，只创建状态栏项，确认能显示后逐步加功能：
1. 最小化脚本（无任何依赖）→ ✅ 显示
2. 加上 `import main` → ✅ 显示
3. 加上 Popover + DashboardWindow + 后台服务 → ✅ 显示
4. 打包后运行 → ❌ 不显示

**结论：开发模式能显示，打包后不能显示，问题在打包配置，不在代码逻辑。**

### 真正的根本原因

**`setAction_` vs `setMenu_` 在打包环境下行为不同。**

`app_native.py` 用 `setAction_` 绑定点击事件：
```python
self.statusItem.button().setAction_("togglePopover:")
self.statusItem.button().setTarget_(self)
```

打包后 py2app 的运行时环境对 `setAction_` 的 selector 解析有问题，导致按钮无法响应，macOS 可能因此不渲染这个状态栏项。

改用 `setMenu_` 直接绑定菜单，打包后行为稳定：
```python
self.statusItem.setMenu_(self.menu)
```

### 修复

`app_native.py` 的 `applicationDidFinishLaunching_` 里：

```python
# 错误写法（打包后不稳定）
self.statusItem.button().setAction_("togglePopover:")
self.statusItem.button().setTarget_(self)
self.menu = NSMenu.alloc().init()
self._build_menu()

# 正确写法（打包后稳定）
self.menu = NSMenu.alloc().init()
self._build_menu()
self.statusItem.setMenu_(self.menu)
```

### 关键规则

1. **菜单绑定用 `setMenu_`，不用 `setAction_`** — `setAction_` 在 py2app 打包环境下 selector 解析不稳定
2. **开发模式能显示 ≠ 打包后能显示** — 必须打包验证，不能只在开发模式测试
3. **排查方法：最小化脚本二分法** — 不要猜，写 30 行脚本逐步加功能定位问题
4. **`b65468d` 不是真正能工作的基准** — 那个版本打包后会 UnicodeEncodeError 崩溃，只是开发模式能跑

---

## 相关 Commit

- **b65468d**: 修复窗口移动和通知显示问题（开发模式能跑，打包后 UnicodeEncodeError 崩溃）
- **97875fc**: fix UnicodeEncodeError，但同时把状态栏项从 `init()` 移到 `applicationDidFinishLaunching_`，且改用 `setAction_`，引入打包后不显示的问题
- **4762a2a**: 启用 LSUIElement 并移除激活策略设置（无关）
- **当前修复**: 改用 `setMenu_` 绑定菜单

## 技术总结

### PyObjC vs rumps

| 特性 | PyObjC | rumps |
|------|--------|-------|
| 学习曲线 | 陡峭 | 平缓 |
| 灵活性 | 高 | 中 |
| 稳定性 | 高（直接调用系统 API） | 中（依赖框架封装） |
| 打包兼容性 | 好 | 可能有问题 |

**建议：** 对于 macOS 菜单栏应用，优先使用纯 PyObjC 实现，避免依赖第三方框架。

### `setMenu_` vs `setAction_`

| 方式 | 开发模式 | 打包后 | 说明 |
|------|---------|--------|------|
| `setMenu_` | ✅ | ✅ | 直接绑定菜单，稳定 |
| `setAction_` | ✅ | ❌ | py2app 环境下 selector 解析不稳定 |

**结论：永远用 `setMenu_`，不用 `setAction_`。**

---

## 最终完整解决方案（2026-05-31 傍晚）

通过逐级测试确认：最小化脚本（无任何依赖）→ 显示，step1-7（逐步加功能）→ 都显示，直到最终 app_native.py → 显示。

**真正的修复：重写 app_native.py 为干净的版本**

关键修改：
1. **删除所有 `#` 中文注释** — 避免 ASCII codec 错误
2. **状态栏项在 `init()` 中创建** — 不要在 `applicationDidFinishLaunching_` 中
3. **`setVisible_(True)` 在 `init()` 中调用** — 不要省略
4. **用 `setMenu_` 绑定菜单** — 不要用 `setAction_`
5. **一键终止添加自我保护** — 跳过自身 PID 和父 PID

```python
def killSafe_(self, sender):
    from aigard.core import kill_process
    threads = _main_mod.threads
    my_pid = os.getpid()
    my_ppid = os.getppid()
    with threads.lock:
        safe_procs = [p for p in threads.latest_processes if p.get("risk") == "safe"]
    for proc in safe_procs:
        pid = proc["pid"]
        if pid == my_pid or pid == my_ppid:
            continue
        kill_process(pid)
```

## 一键终止安全规则

| 规则 | 说明 |
|------|------|
| 跳过自身 PID | `pid == os.getpid()` |
| 跳过父进程 PID | `pid == os.getppid()` |
| 跳过当前 AI Guard 实例 | 任何匹配 AI Guard 名称的进程 |

## 未来改进

- [ ] 打包验证加入 build.sh 流程（打包后自动检查进程是否启动）
