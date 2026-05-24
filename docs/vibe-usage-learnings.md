# 从 Vibe Usage 学到的经验

> 参考项目：https://github.com/vibe-cafe/vibe-usage-app
> 分析日期：2026-05-24

## 项目概述

Vibe Usage 是一个 macOS 菜单栏应用，用于追踪 AI 编程工具的 Token 用量和费用。技术栈为 Swift + SwiftUI，与 AI Guard 的 Python + rumps 方案形成对比。

## 核心亮点

### 1. 专业的菜单栏实现 ⭐⭐⭐⭐⭐

**技术方案：**
- 使用 `NSHostingView` + SwiftUI 在菜单栏显示多行文本
- `PassthroughHostingView` 解决 SwiftUI 吞噬点击事件问题
- 自定义 `PopoverPanel` 带动画（0.22s 打开，0.14s 关闭，缩放 + 位移）

**AI Guard 可借鉴：**
- ✅ **已实现**：rumps 支持多行文本（`\n` 分隔）
- 🔄 **可改进**：考虑使用 PyObjC 实现更精细的菜单栏控制
- 🔄 **可改进**：Web UI 可以添加打开/关闭动画

### 2. 优雅的状态管理 ⭐⭐⭐⭐

**技术方案：**
- Swift 的 `@Observable` 宏（而非 ObservableObject）
- 单一 `AppState` 管理所有状态
- 无 Combine 依赖，更简洁

**AI Guard 可借鉴：**
- ✅ **已实现**：使用全局 `AppState` 类管理状态
- ✅ **已实现**：FastAPI 的依赖注入机制类似

### 3. 性能优化 ⭐⭐⭐⭐⭐

**技术方案：**
- **ScrollWatcher**：防止滚动时图表悬停导致的卡顿
- **单一悬停区域**：一个 `.onContinuousHover` 而非每个柱子一个
- **60秒防抖**：避免频繁刷新数据

**AI Guard 可借鉴：**
- 🔄 **待实现**：Web UI 图表添加滚动优化
- 🔄 **待实现**：实现 60 秒防抖的数据刷新机制
- ✅ **已实现**：SSE 推流已经是高效方案

### 4. 自动更新（Sparkle）⭐⭐⭐⭐

**技术方案：**
- Sparkle 框架集成
- Ed25519 签名验证
- appcast.xml 自动生成
- 版本检查脚本（防止忘记更新版本号）

**AI Guard 可借鉴：**
- ✅ **已实现**：版本检查脚本（`scripts/check-version.sh`）
- 🔄 **待实现**：自动更新机制（可考虑 GitHub Releases API）
- 🔄 **待实现**：应用内更新通知

### 5. 完善的打包流程 ⭐⭐⭐⭐⭐

**技术方案：**
```bash
./scripts/check-version.sh      # 版本一致性检查
./scripts/build-app.sh          # 构建 + 签名
./scripts/build-app.sh --notarize  # 公证
./scripts/generate-appcast.sh   # 生成更新 feed
```

**AI Guard 可借鉴：**
- ✅ **已实现**：版本检查集成到 `build.sh`
- ✅ **已实现**：自动签名
- 🔄 **待实现**：公证流程（如需分发）
- 🔄 **待实现**：自动化发布脚本

### 6. 窗口层级管理 ⭐⭐⭐

**技术方案：**
- `ActivationCoordinator` 智能切换 `NSApp.activationPolicy`
  - popup only → `.accessory`
  - Settings visible → `.regular`
  - 无窗口 → `.prohibited`

**AI Guard 可借鉴：**
- ✅ **已实现**：rumps 自动管理窗口层级
- ✅ **已实现**：LSUIElement 配置正确

## 技术栈对比

| 特性 | Vibe Usage | AI Guard | 评价 |
|------|-----------|----------|------|
| **语言** | Swift | Python | Python 更适合系统监控 ✅ |
| **UI 框架** | SwiftUI | HTML + JS | Web UI 更灵活 ✅ |
| **菜单栏** | NSHostingView | rumps | rumps 更简单 ✅ |
| **状态管理** | @Observable | 全局类 | 都很好 ✅ |
| **打包** | Xcode + SPM | py2app | py2app 有局限 ⚠️ |
| **自动更新** | Sparkle | 无 | 需要添加 🔄 |
| **性能优化** | 精细控制 | 基本优化 | 可改进 🔄 |

## UI/UX 设计亮点

### 配色方案（深色主题）

```css
/* Vibe Usage 的配色 */
--bg-primary:    rgb(10, 10, 10);      /* 0.04 * 255 */
--bg-card:       rgb(23, 23, 23);      /* 0.09 * 255 */
--border:        rgb(41, 41, 41);      /* 0.16 * 255 */
--text-primary:  rgb(255, 255, 255);
--text-secondary: rgb(161, 161, 161);  /* 0.63 * 255 */
--text-tertiary: rgb(97, 97, 97);      /* 0.38 * 255 */
--accent:        rgb(51, 204, 128);    /* 绿色强调 */
```

**AI Guard 可借鉴：**
- 🔄 **待实现**：统一配色方案
- 🔄 **待实现**：CSS 变量管理颜色
- 🔄 **待实现**：更精细的层次感

### 布局设计

- **弹出面板尺寸**：520px × 620px（Vibe Usage）
- **卡片圆角**：4px（小圆角，现代感）
- **边框宽度**：1px（微妙的分隔）
- **字体**：等宽字体显示数字

**AI Guard 当前：**
- 全屏 Web UI（更灵活）
- 响应式设计
- Chart.js 图表

## 已实现的改进

### ✅ 版本检查脚本

**文件：** `scripts/check-version.sh`

**功能：**
- 检查 `CFBundleVersion` 和 `CFBundleShortVersionString` 一致性
- 验证版本格式（X.Y.Z）
- 对比最新 Git tag，确保版本递增
- 检查 README.md 中的版本引用

**集成：** 已集成到 `build.sh` 第一步

## 待实现的改进

### 🔄 优先级 1：自动更新机制

**方案：**
1. 使用 GitHub Releases API 检查更新
2. 应用内显示更新通知
3. 一键下载并安装新版本

**实现步骤：**
- [ ] 创建 `aigard/updater.py` 模块
- [ ] 添加 GitHub API 集成
- [ ] 在菜单栏添加"检查更新"选项
- [ ] 实现下载和安装流程

### 🔄 优先级 2：Web UI 性能优化

**方案：**
1. 添加滚动时的图表优化
2. 实现 60 秒防抖的数据刷新
3. 优化 Chart.js 配置

**实现步骤：**
- [ ] 添加滚动事件监听
- [ ] 实现防抖函数
- [ ] 优化 Chart.js 动画配置

### 🔄 优先级 3：UI 配色优化

**方案：**
1. 参考 Vibe Usage 的配色方案
2. 使用 CSS 变量统一管理
3. 增强视觉层次感

**实现步骤：**
- [ ] 定义 CSS 变量
- [ ] 更新所有组件样式
- [ ] 添加更多视觉细节

### 🔄 优先级 4：发布自动化

**方案：**
1. 创建 `scripts/release.sh` 脚本
2. 自动化 Git tag、GitHub Release 创建
3. 自动上传 .app 和 .dmg

**实现步骤：**
- [ ] 编写发布脚本
- [ ] 集成 GitHub CLI
- [ ] 添加 CHANGELOG 生成

## 不适用的特性

### ❌ Swift/SwiftUI 迁移

**原因：**
- Python 更适合系统监控（psutil）
- 现有代码库成熟稳定
- 迁移成本过高

### ❌ 完全复制 PopoverPanel

**原因：**
- Web UI 提供更好的灵活性
- 不需要 Swift 的精细控制
- rumps 的默认行为已足够

### ❌ Sparkle 框架

**原因：**
- Sparkle 是 macOS 专用
- Python 应用更适合自定义更新机制
- GitHub Releases API 更简单

## 总结

### 核心收获

1. **版本管理的重要性**：自动化检查防止人为错误 ✅
2. **性能优化细节**：防抖、滚动优化等小细节提升体验
3. **专业的打包流程**：完整的脚本化流程
4. **用户体验细节**：动画、配色、布局的精细打磨

### 行动计划

**短期（1-2 周）：**
- [x] 版本检查脚本
- [ ] 自动更新机制
- [ ] Web UI 性能优化

**中期（1 个月）：**
- [ ] UI 配色优化
- [ ] 发布自动化
- [ ] 文档完善

**长期（持续）：**
- [ ] 用户反馈收集
- [ ] 功能迭代
- [ ] 性能监控

## 参考资源

- [Vibe Usage GitHub](https://github.com/vibe-cafe/vibe-usage-app)
- [Vibe Usage AGENTS.md](https://github.com/vibe-cafe/vibe-usage-app/blob/main/AGENTS.md)
- [Sparkle Framework](https://sparkle-project.org/)
- [py2app Documentation](https://py2app.readthedocs.io/)
