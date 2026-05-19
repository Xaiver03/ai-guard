# 进程安全评分规则说明

AI Guard 对每个监控到的进程进行安全评估，给出三个等级：**❌ 不建议操作 / ⚠️ 谨慎 / ✅ 可安全终止**。

---

## 评分等级

| 等级 | 标签 | 建议操作 | 含义 |
|------|------|---------|------|
| `danger` | ❌ 不建议操作 | 不操作 | 终止会直接丢失工作或损坏数据 |
| `caution` | ⚠️ 谨慎（建议先暂停） | 先 SIGSTOP 暂停 | 可能正在工作，操作需确认 |
| `safe` | ✅ 可安全终止 | 直接 SIGTERM 终止 | 终止后无损失，可重启恢复 |

---

## 规则详解（按优先级）

### 规则 D — 高危进程（最高优先级，不被其他规则覆盖）

匹配以下**名称或命令行关键字**时直接判定为 `danger`：

| 关键字 | 原因 |
|--------|------|
| `claude` | Claude Code 进程，终止会中断 AI 任务并丢失上下文 |
| `codex` | Codex Agent 进程，终止会中断任务 |
| `terminal` | 系统终端窗口，**关闭终端 = 关闭其中运行的所有 AI 会话** |
| `iterm` | iTerm2 终端窗口，同上 |
| `ghostty` / `warp` / `hyper` | 其他终端宿主，同上 |
| `tmux` / `screen` | 终端会话管理器，终止会关闭所有托管会话 |
| `cursor` | Cursor 编辑器主进程，终止关闭编辑器 |
| `code helper` | VS Code 核心进程，终止影响编辑器 |
| `mysql` / `postgres` / `mongod` | 数据库，强制终止可能损坏数据 |
| `redis-server` | Redis，终止会丢失未持久化数据 |
| `docker` / `containerd` | 容器运行时，终止会停止所有容器 |

> **为什么终端窗口是 danger？**
> Claude Code 和 Codex 都运行在终端 shell 里。如果批量操作误关了 iTerm2 或 Terminal.app，正在进行的 AI 编程任务会立即中断，未保存的修改和上下文全部丢失。因此终端宿主进程强制设为不可操作。

---

### 规则 C1 — CPU 正在忙

- 触发条件：`cpu_percent > 20%`
- 结果：`caution`，建议先暂停（SIGSTOP），观察后再决定是否终止

---

### 规则 S1 — 语言服务器

- 匹配：`pylance`、`pyright`、`typescript-language-server`、`rust-analyzer`、`clangd`、`gopls` 等
- 结果：`safe`
- 原因：IDE 检测到语言服务器退出后会自动重启，终止后无损失，且往往占用 300MB~2GB 内存

---

### 规则 S2 — 构建/编译/测试工具

- 匹配：`webpack`、`vite`、`tsc`、`uni`、`jest`、`pytest`、`cargo`、`gradle` 等
- 结果：`safe`
- 原因：构建工具被终止后，重新执行构建命令即可恢复，不会丢失任何源码

---

### 规则 S3 — 冗余实例（同名进程 ≥ 3 个）

- 触发条件：系统中同名进程数量 ≥ 3
- 结果：提升为 `safe`（若原来不是 `danger`）
- 原因：大量同名进程通常是工具的子进程池，关掉部分不影响主流程

---

### 规则 S4 — 长时间空转

- 触发条件：运行超过 1 小时 **且** CPU < 1% **且** 内存 > 200MB
- 结果：提升为 `safe`
- 原因：进程长时间占着内存但不做任何工作，属于资源浪费，终止后如需要重新启动即可

---

## 自动终止逻辑（Auto-Kill）

在 `config.toml` 中配置：

```toml
[auto_kill]
enabled = false         # 是否开启自动终止
mem_trigger_pct = 85    # 触发阈值：内存使用率 ≥ 此值时开始自动终止
swap_trigger_pct = 75   # 触发阈值：Swap 使用率 ≥ 此值时开始自动终止
target_mem_pct = 70     # 目标：终止足够多进程使内存降到此值以下
cooldown_sec = 120      # 两次自动终止之间的最小间隔（秒）
```

**自动终止只针对评分为 `safe` 的进程**，按内存占用从大到小依次终止，直到内存压力降到目标值以下。`caution` 和 `danger` 进程永远不会被自动终止。

---

## 如何自定义规则

编辑 `advisor.py` 中的三个列表：
- `_DANGER_PATTERNS` — 添加你不想被触碰的进程关键字
- `_SAFE_BUILD_PATTERNS` — 添加你的构建工具
- `_LANG_SERVER_PATTERNS` — 添加你的语言服务器

格式：
```python
# 带自定义说明：
("my-tool", "这是我的工具，请勿终止")

# 简单匹配（在 SAFE 列表中）：
"my-build-tool",
```
