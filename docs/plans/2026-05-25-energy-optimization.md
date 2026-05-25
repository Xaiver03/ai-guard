# AI Guard 能耗优化实施记录

**日期：** 2026-05-25  
**版本：** v1.1.3  
**目标：** 降低 macOS 菜单栏应用的 CPU 占用和能耗

---

## 问题诊断

通过代码审查发现 **7 个严重能耗问题**：

| 问题 | 位置 | 原始间隔 | 影响 |
|------|------|---------|------|
| SSE 推流过于频繁 | routes.py:347 | 3秒 | 每3秒序列化JSON并推送 |
| 菜单栏定时器过于频繁 | app_menubar.py:140 | 5秒 | 每5秒更新UI状态 |
| 监控采集过于频繁 | config.toml:8 | 5秒 | 每5秒调用 psutil |
| 黑名单 busy-wait | threads.py:145 | 1秒轮询 | 即使黑名单为空仍每秒唤醒 |
| 自动终止 busy-wait | threads.py:79 | 5秒轮询 | 即使禁用仍每5秒唤醒 |
| Usage 刷新过于频繁 | threads.py:226 | 5分钟 | 每5分钟扫描文件系统 |
| 菜单栏轮询检查 | app_menubar.py:209 | 每5秒检查 | 轮询检查是否需要刷新 |

---

## 优化方案

### 1. **SSE 推流间隔优化** (routes.py)
- **修改：** 3秒 → 15秒
- **预计降低：** 80% 能耗
- **影响：** 前端图表更新延迟从3秒变为15秒，用户无感知

```python
# routes.py:347
await asyncio.sleep(15)  # 原 3 秒
```

---

### 2. **菜单栏定时器优化** (app_menubar.py)
- **修改：** 5秒 → 15秒
- **预计降低：** 67% 能耗
- **影响：** 菜单栏状态更新延迟15秒，用户无感知

```python
# app_menubar.py:140
self._timer = rumps.Timer(self._refresh_status, 15)  # 原 5 秒
```

---

### 3. **监控采集间隔优化** (config.toml)
- **修改：** 5秒 → 15秒
- **预计降低：** 67% 能耗
- **影响：** 历史数据点间隔变大，但 60 点仍覆盖 15 分钟历史

```toml
# config.toml:8
interval_sec = 15  # 原 5 秒
```

---

### 4. **黑名单轮询优化** (threads.py)
- **修改：** 1秒固定轮询 → 事件驱动 + 5秒检查
- **预计降低：** 90% 能耗（黑名单为空时）
- **实现：** 使用 `threading.Event`，黑名单为空时休眠等待

```python
# threads.py:145
def _block_loop(self):
    while True:
        if not self.blocked_processes:
            # 无黑名单时休眠，等待被唤醒
            self._block_event.wait(timeout=60)
            self._block_event.clear()
            continue
        # 有黑名单时每5秒检查
        time.sleep(5)
```

**API 配合：** 添加黑名单时唤醒线程
```python
# routes.py:440
threads_manager._block_event.set()
```

---

### 5. **自动终止轮询优化** (threads.py)
- **修改：** 5秒固定轮询 → 事件驱动 + 15秒检查
- **预计降低：** 90% 能耗（禁用时）
- **实现：** 使用 `threading.Event`，禁用时休眠等待

```python
# threads.py:79
def _auto_kill_loop(self):
    while True:
        if not self.autokill_enabled:
            # 禁用时休眠，等待被唤醒
            self._autokill_event.wait(timeout=60)
            self._autokill_event.clear()
            continue
        # 启用时每15秒检查
        time.sleep(15)
```

**API 配合：** 启用自动终止时唤醒线程
```python
# routes.py:229
if state:
    threads_manager._autokill_event.set()
```

---

### 6. **Usage 刷新间隔优化** (threads.py)
- **修改：** 5分钟 → 10分钟
- **预计降低：** 50% 能耗
- **影响：** 使用统计更新延迟变长，但仍保持实时性

```python
# threads.py:226
REFRESH_INTERVAL = 600  # 原 300 秒（5分钟）
```

---

### 7. **菜单栏 Usage 刷新优化** (app_menubar.py)
- **修改：** 每5秒轮询检查 → `threading.Timer` 定时触发
- **预计降低：** 避免不必要的时间检查
- **实现：** 使用 Timer 自动重调度

```python
# app_menubar.py:215
def _schedule_usage_refresh(self):
    def _refresh_and_reschedule():
        self._auto_refresh_usage()
        if self._usage_refresh_interval > 0:
            self._schedule_usage_refresh()
    
    timer = threading.Timer(self._usage_refresh_interval, _refresh_and_reschedule)
    timer.daemon = True
    timer.start()
```

---

## 优化效果预估

| 组件 | 原间隔 | 新间隔 | 能耗降低 |
|------|--------|--------|---------|
| SSE 推流 | 3秒 | 15秒 | **80% ↓** |
| 菜单栏定时器 | 5秒 | 15秒 | **67% ↓** |
| 监控采集 | 5秒 | 15秒 | **67% ↓** |
| 黑名单轮询 | 1秒 | 事件驱动 | **90% ↓** |
| 自动终止轮询 | 5秒 | 事件驱动 | **90% ↓** |
| Usage 刷新 | 5分钟 | 10分钟 | **50% ↓** |
| 菜单栏轮询检查 | 每5秒 | Timer | **100% ↓** |

**综合预估：整体能耗降低 60-75%**

---

## 用户体验影响

✅ **无感知变化：**
- 15秒的延迟对菜单栏应用完全可接受
- 图表更新延迟不影响监控效果
- 黑名单和自动终止功能逻辑不变

✅ **性能提升：**
- CPU 占用显著降低
- 电池续航延长
- 系统响应更流畅

---

## 验证步骤

1. **打包应用**
   ```bash
   ./build.sh
   ```

2. **安装到 /Applications**
   ```bash
   cp -r "dist/AI Guard.app" /Applications/
   ```

3. **启动应用**
   ```bash
   open "/Applications/AI Guard.app"
   ```

4. **监控能耗**
   - 打开 **活动监视器** → **能耗** 标签页
   - 观察 "AI Guard" 的能耗影响值
   - 对比优化前后的 CPU 占用百分比

5. **功能验证**
   - 打开 Web UI (http://localhost:8765)
   - 验证实时图表更新（15秒间隔）
   - 验证菜单栏状态显示（15秒刷新）
   - 测试黑名单功能（添加/移除进程）
   - 测试自动终止功能（开启/关闭）

---

## 后续优化建议

如果仍需进一步降低能耗，可考虑：

1. **按需启动后台线程**
   - Usage 刷新线程：仅在用户打开 usage.html 时启动
   - 定时终止线程：仅在启用时启动

2. **更长的间隔**
   - 监控采集：15秒 → 30秒（夜间模式）
   - SSE 推流：15秒 → 30秒（无活动连接时）

3. **智能休眠**
   - 检测用户活动，无活动时降低采集频率
   - 使用 macOS 电源管理 API 感知电池状态

---

## 技术细节

### 事件驱动模式

使用 `threading.Event` 替代 busy-wait：

```python
# 初始化
self._block_event = threading.Event()
self._autokill_event = threading.Event()

# 线程中等待
self._block_event.wait(timeout=60)  # 最多等待60秒
self._block_event.clear()

# API 中唤醒
threads_manager._block_event.set()
```

**优势：**
- 禁用/空闲时 CPU 占用接近 0
- 启用时立即响应（无需等待轮询周期）
- 超时机制防止永久阻塞

---

## 修改文件清单

- ✅ `aigard/api/routes.py` - SSE 间隔、黑名单/自动终止唤醒
- ✅ `aigard/core/threads.py` - 事件驱动、Usage 间隔
- ✅ `app_menubar.py` - 定时器间隔、Timer 替代轮询
- ✅ `config.toml` - 监控采集间隔
- ✅ `main.py` - 默认间隔值

---

## 版本信息

- **优化前版本：** v1.1.2
- **优化后版本：** v1.1.3
- **Git Commit：** (待提交)
- **发布日期：** 2026-05-25
