# Mac App Store 上架可行性分析

## 结论：❌ 不建议上架 Mac App Store

AI Guard 更适合通过 **独立分发（DMG）** 的方式发布，原因如下：

---

## 主要障碍

### 1. 沙盒限制（Sandboxing）

Mac App Store 要求所有应用必须启用 **App Sandbox**，这会导致以下功能无法使用：

| 功能 | 需要的权限 | App Sandbox 是否允许 |
|------|-----------|---------------------|
| 读取所有进程信息 | `psutil.process_iter()` | ❌ 只能读取自己的进程 |
| 终止/暂停其他进程 | `os.kill(pid, signal)` | ❌ 无法操作其他进程 |
| 读取 `~/.claude` 目录 | 文件系统访问 | ❌ 需要用户手动授权 |
| 读取 Safari 书签 | `~/Library/Safari/Bookmarks.plist` | ❌ 需要用户手动授权 |
| 监控系统资源 | `psutil.virtual_memory()` | ⚠️ 部分允许，但受限 |

**核心问题：** AI Guard 的核心功能是"监控和干预其他进程"，这与 App Sandbox 的设计理念冲突。

### 2. 权限申请（Entitlements）

即使申请了以下权限，也可能被拒：

```xml
<!-- 需要但可能被拒的权限 -->
<key>com.apple.security.temporary-exception.apple-events</key>
<string>允许发送 Apple Events 终止进程</string>

<key>com.apple.security.temporary-exception.files.absolute-path.read-only</key>
<array>
    <string>/Users/*/Library/Safari/Bookmarks.plist</string>
    <string>/Users/*/.claude/</string>
</array>
```

**Apple 审核标准：** 只有"系统工具"类应用（如 CleanMyMac、iStat Menus）才可能获批，且需要详细说明必要性。

### 3. 审核风险

| 审核点 | AI Guard 的情况 | 风险等级 |
|--------|----------------|---------|
| 进程监控 | 读取所有系统进程 | 🔴 高 |
| 进程干预 | 暂停/终止其他应用 | 🔴 高 |
| 文件访问 | 读取 `~/.claude` 和 Safari 书签 | 🟡 中 |
| 通知推送 | macOS 原生通知 | 🟢 低 |
| 网络请求 | 检查更新（GitHub API） | 🟢 低 |

**预计审核结果：** 大概率被拒，理由可能是：
- "应用访问了过多系统资源"
- "进程干预功能可能影响系统稳定性"
- "未充分说明为何需要这些权限"

### 4. 打赏限制

Mac App Store 要求所有付费功能必须走 **App 内购买（IAP）**：

- ❌ 不能在应用内放支付宝/微信收款码
- ❌ 不能在应用内放爱发电链接
- ❌ 不能在应用内放 GitHub Sponsors 链接
- ✅ 只能在 App Store 产品页面的"开发者网站"链接中引导

**Apple 抽成：** 如果走 IAP，Apple 抽 30%（¥6 → 你只能拿 ¥4.2）

### 5. 更新流程

| 对比项 | 独立分发（DMG） | Mac App Store |
|--------|----------------|---------------|
| 更新速度 | 立即发布 | 需要 1-3 天审核 |
| 紧急修复 | 立即推送 | 等待审核 |
| Beta 测试 | 随时发布 | 需要 TestFlight |
| 版本回滚 | 用户自行下载旧版 | 无法回滚 |

---

## 独立分发的优势

### ✅ 你现在的方式（推荐）

1. **功能完整** — 无沙盒限制，所有功能正常工作
2. **快速迭代** — 随时发布新版本，无需等待审核
3. **打赏自由** — 支付宝/微信/爱发电，100% 收入归你
4. **用户信任** — Developer ID 签名 + Apple 公证，用户可直接安装
5. **开源透明** — GitHub 开源，用户可审查代码

### 📊 对比表

| 项目 | 独立分发（DMG） | Mac App Store |
|------|----------------|---------------|
| 功能完整性 | ✅ 100% | ❌ 受沙盒限制 |
| 审核时间 | ✅ 无需审核 | ❌ 1-3 天 |
| 打赏收入 | ✅ 100% | ❌ 70%（Apple 抽 30%） |
| 更新速度 | ✅ 立即 | ❌ 等待审核 |
| 用户安装 | ⚠️ 需手动下载 | ✅ App Store 一键安装 |
| 曝光度 | ⚠️ 需自行推广 | ✅ App Store 搜索 |

---

## 如果一定要上架 App Store

### 方案 A：阉割版（不推荐）

移除以下功能，只保留基础监控：

- ❌ 移除进程干预（暂停/终止）
- ❌ 移除所有进程视图
- ❌ 移除书签管理
- ❌ 移除 Claude 使用统计（需要读取 `~/.claude`）
- ✅ 保留系统资源监控（CPU/内存/Swap/磁盘）
- ✅ 保留告警通知

**结果：** 变成一个"系统监控仪表盘"，失去核心价值。

### 方案 B：双版本策略

- **App Store 版** — 阉割版，只做监控和告警
- **独立分发版** — 完整版，包含所有功能

**问题：**
- 维护两套代码
- 用户困惑（为什么功能不一样？）
- App Store 版可能因"功能不完整"被拒

---

## 推广建议（独立分发）

既然不上架 App Store，如何提高曝光度？

### 1. 技术社区

- **少数派** — 投稿"效率工具"专栏
- **V2EX** — 发布在 /go/create 节点
- **掘金** — 发布技术文章 + 工具介绍
- **知乎** — 回答"Mac 有哪些好用的开发工具？"

### 2. 社交媒体

- **Twitter/X** — 发布演示视频，带 #macOS #AI #开发工具 标签
- **微博** — 发布到"数码"话题
- **即刻** — 发布到"独立开发者"圈子

### 3. 产品目录

- **Product Hunt** — 提交到 Product Hunt（国际曝光）
- **Indie Hackers** — 分享开发故事
- **GitHub Trending** — 优化 README，争取上榜

### 4. SEO 优化

在 README 和文档中添加关键词：

- "Mac AI 开发工具"
- "Claude Code 内存监控"
- "Cursor 资源管理"
- "macOS 菜单栏工具"

### 5. 视频演示

录制 1-2 分钟演示视频：

1. 问题场景：Claude Code 跑满内存
2. 安装 AI Guard
3. 实时监控 + 告警
4. 一键终止安全进程
5. 系统恢复正常

上传到：
- YouTube（国际用户）
- B站（国内用户）
- 抖音/快手（短视频）

---

## 总结

**不建议上架 Mac App Store**，原因：

1. 核心功能（进程监控/干预）与沙盒限制冲突
2. 审核大概率被拒
3. 打赏收入被 Apple 抽 30%
4. 更新速度慢

**推荐继续独立分发**，优势：

1. 功能完整，无限制
2. 快速迭代，无审核
3. 打赏自由，100% 收入
4. Developer ID 签名 + Apple 公证，用户信任度高

**提高曝光度的方法：**

- 技术社区投稿（少数派、V2EX、掘金）
- 社交媒体推广（Twitter、微博、即刻）
- 产品目录提交（Product Hunt、Indie Hackers）
- SEO 优化 + 视频演示

---

## 参考资料

- [Mac App Store 审核指南](https://developer.apple.com/app-store/review/guidelines/)
- [App Sandbox 设计指南](https://developer.apple.com/library/archive/documentation/Security/Conceptual/AppSandboxDesignGuide/)
- [独立分发 vs App Store](https://developer.apple.com/support/compare-memberships/)
