# 菜单栏图标修复记录

> 日期：2026-05-25
> 问题：更换新 logo 后菜单栏图标无法正常显示

---

## 问题背景

更换新的彩色盾牌 logo 后，菜单栏图标出现多种异常：图标不显示、短暂出现后消失、显示为黑色矩形。

## 排查过程与发现的问题

### 问题 1：端口占用导致应用启动失败

**现象**：应用进程在运行，但菜单栏无图标，服务器也无响应。

**原因**：开发模式的 `python main.py` 占用了 8765 端口，打包后的应用启动 FastAPI 时报 `OSError: [Errno 48] Address already in use`。

**修复**：添加 `_kill_stale_processes()` 函数，在应用启动时自动清理旧进程和占用的端口。

```python
def _kill_stale_processes():
    # 1. 杀掉占用端口的进程
    # 2. 杀掉同名旧进程
```

### 问题 2：图标短暂出现后消失

**现象**：启动后图标闪现约 1 秒，然后消失。

**原因**：`_refresh_status()` 定时器每 15 秒执行一次，其中两行代码导致图标丢失：

```python
# 第一个问题：用 SF Symbol 覆盖了静态 PNG 图标
self.icon = _sf_symbol_to_png(symbol_name)  # SF Symbol 可能加载失败

# 第二个问题：设置 title=None 触发 rumps 的 fallbackOnName()
self.title = None  # 如果 image 也为空，rumps 会用应用名称替代图标
```

`rumps` 内部的 `fallbackOnName()` 逻辑：
```python
def fallbackOnName(self):
    if not (self.nsstatusitem.title() or self.nsstatusitem.image()):
        self.nsstatusitem.setTitle_(self._app['_name'])
```

当 `self.title = None` 被调用时，`setStatusBarTitle()` → `fallbackOnName()` 链式触发，如果此时 `image()` 为空就会用文字替代图标。

**修复**：移除 `_refresh_status()` 中的 `self.icon` 和 `self.title` 赋值，初始化后不再修改菜单栏图标。

### 问题 3：Popover 自定义点击行为后图标丢失

**现象**：`_init_popover()` 设置自定义 `button.setTarget_()` / `button.setAction_()` 后图标消失。

**原因**：替换按钮的 target/action 后，需要重新设置图标。

**修复**：在 `_init_popover()` 末尾显式调用 `nsstatusitem.setImage_()` 和 `button.setImage_()`。

### 问题 4：图标显示为黑色矩形

**现象**：图标区域显示为一个纯黑色的矩形，没有盾牌形状。

**原因**：原始 logo 的背景是**白色不透明**（RGBA: 1.0, 1.0, 1.0, 1.0），不是透明的。转换为黑色图标时，背景也被转成了黑色，导致整个图标变成一个黑色矩形。

验证方法：
```python
r, g, b, a = rep.colorAtX_y_(0, 0).getRed_green_blue_alpha_(None, None, None, None)
# 左上角: r=1.00 g=1.00 b=1.00 a=1.00 → 白色不透明（不是透明！）
```

**修复**：逐像素处理，白色背景 → 透明，其他颜色 → 纯黑色：

```python
if r > 240 and g > 240 and b > 240:
    # 白色/近白色背景 → 完全透明
    alpha = 0
else:
    # 图标内容 → 纯黑色，保留原始 alpha
    r, g, b = 0, 0, 0
```

### 问题 5：py2app 打包路径错误

**现象**：打包后的 .app 启动时报 `AttributeError: module 'sys' has no attribute '_MEIPASS'`。

**原因**：`sys._MEIPASS` 是 PyInstaller 的属性，py2app 不使用它。

**修复**：使用 `Path(__file__).parent` 替代，py2app 打包后 `__file__` 指向 `Contents/Resources/app_menubar.py`，路径解析正确。

## macOS 菜单栏图标规范

| 要求 | 说明 |
|------|------|
| 颜色 | 纯黑色（RGB 0,0,0），macOS 自动处理深浅模式 |
| 背景 | 必须透明（alpha=0） |
| 模式 | `template=True`，让系统自动适配深色/浅色菜单栏 |
| 尺寸 | 22x22 pt（44x44 px @2x Retina） |
| 格式 | PNG，带 alpha 通道 |

**关键**：template 模式下，macOS 只看 alpha 通道来决定图标形状，黑色像素被视为前景，透明像素被视为背景。如果背景不透明，整个图标区域都会被填充。

## 最终方案

```
logo.png (彩色, 白色背景)
    ↓ 逐像素处理
    ↓ 白色(>240) → alpha=0 (透明)
    ↓ 其他颜色 → RGB(0,0,0) 保留 alpha
    ↓
icon_template.png (纯黑色, 透明背景, 1254x1254)
    ↓ sips -z 44 44
    ↓
menubar_icon.png (纯黑色, 透明背景, 44x44 @2x)
    ↓
rumps.App(icon=menubar_icon.png, template=True, title=None)
```

## 涉及的文件

| 文件 | 修改内容 |
|------|----------|
| `app_menubar.py` | 添加启动清理、修复图标初始化、移除定时器中的图标覆盖 |
| `assets/menubar_icon.png` | 新生成的纯黑色透明背景菜单栏图标 |
| `assets/icon_template.png` | 中间产物，1254x1254 纯黑色透明背景 |
| `setup.py` | DATA_FILES 中添加 menubar_icon.png |
| `aigard/popover/view_builder.py` | Popover 面板 UI 布局（容器高度 520） |
