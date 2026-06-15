"""advisor.py — 进程安全终止评估"""

import time
from dataclasses import dataclass
from typing import List

import psutil

# ── 评分规则可配置参数(可由 main.py 运行时动态修改)──────────
CPU_CAUTION_PCT = 20      # CPU > 此值 → caution
IDLE_MIN_MINUTES = 120    # 运行 > 此值(分钟)且 CPU<1% → safe (2小时空转判定)


@dataclass(slots=True)
class ProcessAdvice:
    """对单个进程的评估结果"""
    pid: int
    risk: str
    label: str
    reasons: List[str]
    action: str


# 已知进程规则(详细说明见 SCORING.md)
#
# 高危:终止会直接丢失工作或损坏数据
# 注意:这里只包含真正危险的进程,普通应用(微信、浏览器等)不应在此列表
_DANGER_PATTERNS = [
    # 数据库(终止可能损坏数据)
    ("mysql",               "数据库进程,强制终止可能损坏数据"),
    ("postgres",            "数据库进程,强制终止可能损坏数据"),
    ("mongod",              "数据库进程,强制终止可能损坏数据"),
    ("redis-server",        "Redis 服务,终止会丢失未持久化数据"),
    # 容器
    ("docker",              "Docker 守护进程,终止会停止所有容器"),
    ("containerd",          "容器运行时,终止会影响所有容器"),
]

# 重要应用:终止会中断工作但可手动重启,标记为 caution 而非 danger
# 这些进程在"所有进程"视图中显示,允许用户手动终止
_CAUTION_PATTERNS = [
    # AI Agent 本体
    ("claude",              "Claude Code 会话窗口,终止会中断 AI 任务"),
    ("codex",               "Codex Agent 进程,终止会中断任务"),
    # 终端宿主
    ("terminal",            "系统终端窗口,关闭会终止其中所有进程"),
    ("iterm",               "iTerm2 终端窗口,关闭会终止其中所有进程"),
    ("ghostty",             "Ghostty 终端,关闭会终止其中所有进程"),
    ("warp",                "Warp 终端,关闭会终止其中所有进程"),
    ("hyper",               "Hyper 终端,关闭会终止其中所有进程"),
    ("tmux",                "tmux 会话管理器,终止会关闭所有托管的终端会话"),
    ("screen",              "screen 会话,终止会丢失会话内容"),
    # 编辑器
    ("cursor",              "Cursor 编辑器主进程,终止会关闭编辑器"),
    ("code helper",         "VS Code 核心辅助进程,终止会影响编辑器"),
    # 浏览器主进程
    ("dia",                 "Dia 浏览器主进程,终止会关闭所有标签页"),
    ("safari",              "Safari 浏览器主进程,终止会关闭所有标签页"),
    ("chrome",              "Chrome 浏览器主进程,终止会关闭所有标签页"),
    ("edge",                "Edge 浏览器主进程,终止会关闭所有标签页"),
    ("firefox",             "Firefox 浏览器主进程,终止会关闭所有标签页"),
    # 通讯应用主进程
    ("wechat",              "微信主进程,终止会关闭微信"),
    ("lark",                "飞书主进程,终止会关闭飞书"),
    ("feishu",              "飞书主进程,终止会关闭飞书"),
    ("qq",                  "QQ 主进程,终止会关闭 QQ"),
    ("dingtalk",            "钉钉主进程,终止会关闭钉钉"),
    # 其他重要应用
    ("figma",               "Figma 设计工具,终止会关闭未保存的设计"),
    ("wpsoffice",           "WPS 办公套件,终止会关闭未保存的文档"),
    ("quark",               "夸克浏览器,终止会关闭所有标签页"),
    ("baidunetdisk",        "百度网盘,终止会中断下载/上传"),
    ("cmux",                "cmux 终端复用器,终止会关闭所有会话"),
]

# MCP 进程特征(Claude Code 的子进程,可以按正常规则评分)
# 注意:必须在 DANGER 检查之前判断,避免误杀会话窗口
_MCP_PATTERNS = [
    # 通用 MCP 模式
    "mcp-server",
    "mcp_server",
    "/mcp/",
    "/.claude/mcp",
    "/.pencil/mcp",
    "@modelcontextprotocol/server",  # npm exec @modelcontextprotocol/server-*
    "modelcontextprotocol",

    # 官方 MCP 服务器
    "server-filesystem",
    "server-github",
    "server-memory",
    "server-git",
    "server-fetch",
    "server-time",

    # 搜索引擎 MCP
    "open-websearch",
    "brave-search-mcp-server",
    "@brave/brave-search",
    "search-baidu",
    "search-bing",
    "search-duckduckgo",
    "search-csdn",
    "search-juejin",
    "search-startpage",
    "search-bilibili",

    # Pencil 设计工具 MCP
    "pencil.app/contents/resources",
    "mcp-server-darwin-arm64",

    # 其他常见 MCP 服务器
    "server-postgres",
    "server-sqlite",
    "server-puppeteer",
    "server-slack",
    "server-linear",
    "server-notion",
]

# 构建/编译/测试工具:可安全终止,重新运行即可
_SAFE_BUILD_PATTERNS = [
    "webpack",
    "vite",
    "rollup",
    "esbuild",
    "tsc",           # TypeScript Compilation
    "uni ",          # uni-app Building
    "next build",
    "nuxt build",
    "parcel",
    "turbopack",
    "jest",
    "vitest",
    "mocha",
    "pytest",
    "cargo",         # Rust Building
    "gradle",
    "mvn",           # Maven
    "bazel",
    "make",
    "cmake",
]

# 语言服务器:内存大但 IDE 会自动重启
_LANG_SERVER_PATTERNS = [
    "pylance",
    "pyright",
    "typescript-language-server",
    "rust-analyzer",
    "clangd",
    "gopls",
    "jdtls",
    "solargraph",
]


def _match_any(haystack: str, patterns) -> str:
    """返回第一个匹配的理由,没有则返回空字符串"""
    for item in patterns:
        if isinstance(item, tuple):
            kw, reason = item
            if kw in haystack:
                return reason
        else:
            if item in haystack:
                return item
    return ""


def _count_same_name(name: str) -> int:
    """统计同名进程数量"""
    count = 0
    for p in psutil.process_iter(["name"]):
        try:
            if (p.info["name"] or "").lower() == name.lower():
                count += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return count


def _uptime_hours(create_time: float) -> float:
    return (time.time() - create_time) / 3600


def advise(proc_info: dict, name_counts: dict | None = None) -> ProcessAdvice:
    """
    # 对一个进程给出评估结论.
    # 评分规则详见 SCORING.md.
    # proc_info 是 monitor.collect_ai_processes 返回的 dict.
    # name_counts: 可选的进程名计数字典(避免重复扫描)
    """
    pid = proc_info["pid"]
    name = proc_info["name"].lower()
    cmdline = proc_info["cmdline"].lower()
    mem_mb = proc_info["mem_mb"]
    cpu = proc_info["cpu_percent"]
    create_time = proc_info["create_time"]
    haystack = f"{name} {cmdline}"

    reasons = []
    risk = "caution"  # [CN] 默认谨慎,需要满足条件才能变为 safe
    action = "pause"

    # 规则 MCP: MCP 子进程优先按正常规则评分(不受 danger/caution 保护)
    is_mcp = _match_any(haystack, _MCP_PATTERNS)
    if is_mcp:
        reasons.append("Claude Code MCP 子进程")
        # 跳过 danger/caution 检查,继续后续规则
    else:
        # 规则 D: 高危进程(数据库、容器等,终止会损坏数据)
        danger_reason = _match_any(haystack, _DANGER_PATTERNS)
        if danger_reason:
            reasons.append(danger_reason)
            if cpu > 5:
                reasons.append(f"CPU 占用 {cpu:.1f}%,正在执行任务")
                return ProcessAdvice(pid, "danger", "❌ 不建议操作", reasons, "leave")
            else:
                reasons.append("CPU 当前较低,可暂停后观察,但仍需谨慎")
                return ProcessAdvice(pid, "danger", "❌ 不建议操作", reasons, "leave")

        # 规则 C2: 重要应用(微信、浏览器、编辑器等,终止会中断工作但可重启)
        # 注意:Claude Code 的 node 进程(cmdline 含 claude)属于 AI 会话,应受保护
        caution_reason = _match_any(haystack, _CAUTION_PATTERNS)
        if caution_reason:
            reasons.append(caution_reason)
            # AI Agent 进程(claude/codex)不能被空转规则降级为 safe
            if "claude" in haystack or "codex" in haystack:
                risk = "caution"
                action = "pause"
            else:
                # 其他应用(微信、浏览器等)空转时可降级为 safe
                risk = "caution"
                action = "pause"

    # 规则 C1:CPU 正在忙
    if cpu > CPU_CAUTION_PCT:
        reasons.append(f"CPU {cpu:.1f}%,进程正在活跃工作")
        risk = "caution"
        action = "pause"

    # ── 规则 S1:语言服务器(内存大但可重启)────────────────────
    lang_match = _match_any(haystack, _LANG_SERVER_PATTERNS)
    if lang_match:
        reasons.append(f"语言服务器({lang_match}),IDE 重启后自动恢复")
        if mem_mb > 300:
            reasons.append(f"内存 {mem_mb:.0f} MB,高内存语言服务器,终止可释放大量内存")
        risk = "safe"
        action = "kill"

    # ── 规则 S2:构建/测试工具 ───────────────────────────────
    build_match = _match_any(haystack, _SAFE_BUILD_PATTERNS)
    if build_match:
        reasons.append(f"构建/测试工具({build_match}),终止后可重新运行")
        risk = "safe"
        action = "kill"

    # ── 规则 S3:多个同名进程(冗余实例)────────────────────────
    # 注意:MCP 进程不适用此规则,因为多个 node 进程可能都在工作
    # 使用预计算的 name_counts,避免每个进程都扫描一次
    if not is_mcp:
        if name_counts is not None:
            same_count = name_counts.get(proc_info["name"].lower(), 1)
        else:
            same_count = _count_same_name(proc_info["name"])

        if same_count >= 3:
            reasons.append(f"同名进程共 {same_count} 个,存在冗余实例,关闭部分通常不影响主流程")
            # AI Agent 进程不能被同名规则降级为 safe
            if "claude" in haystack or "codex" in haystack:
                pass  # 保持当前风险等级
            elif risk != "danger":
                risk = "safe"
                action = "kill"

    # ── 规则 S4:长时间空转 ──────────────────────────────────
    uptime_minutes = (time.time() - create_time) / 60
    if uptime_minutes > IDLE_MIN_MINUTES and cpu < 1:
        reasons.append(f"运行 {uptime_minutes:.0f} 分钟,CPU ≈ 0,判定为空转进程")
        # AI Agent 进程不能被降级为 safe
        if "claude" in haystack or "codex" in haystack:
            pass  # 保持当前风险等级(caution),不降级
        elif risk == "danger":
            pass  # danger 保持不动
        else:
            risk = "safe"
            action = "kill"

    # ── 参考信息:内存占用 ───────────────────────────────────
    if mem_mb > 1000:
        reasons.append(f"⚠ 内存 {mem_mb:.0f} MB,属于高内存进程")
    elif mem_mb > 500:
        reasons.append(f"内存 {mem_mb:.0f} MB,中等内存占用")

    # ── 兜底 ────────────────────────────────────────────────
    if not reasons:
        reasons.append("普通进程,终止后可重新启动")

    # ── GenerationTag ─────────────────────────────────────────────
    if risk == "safe":
        label = "✅ 可安全终止"
    elif risk == "caution":
        label = "⚠️ 谨慎(建议先暂停)"
        action = "pause"
    else:
        label = "❌ 不建议操作"
        action = "leave"

    return ProcessAdvice(pid, risk, label, reasons, action)


def _build_name_counts() -> dict[str, int]:
    """一次性构建系统进程名计数字典"""
    counts: dict[str, int] = {}
    for p in psutil.process_iter(["name"]):
        try:
            name = (p.info["name"] or "").lower()
            counts[name] = counts.get(name, 0) + 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return counts


def advise_list(proc_list: list) -> list:
    """批量评估,返回附带 advice 字段的进程列表

    # 一次性构建进程名计数字典,避免每个进程都做一次全量扫描.
    """
    # 一次扫描,所有进程共享
    name_counts = _build_name_counts()

    result = []
    for p in proc_list:
        adv = advise(p, name_counts=name_counts)
        enriched = dict(p)
        enriched["risk"] = adv.risk
        enriched["risk_label"] = adv.label
        enriched["risk_reasons"] = adv.reasons
        enriched["suggested_action"] = adv.action
        result.append(enriched)
    return result
