# AI Guard 分发指南

> 本文档说明如何打包、签名、公证、发布 AI Guard 的 macOS 应用

## 目录

- [打包流程](#打包流程)
- [签名与公证](#签名与公证)
- [发布到 GitHub Release](#发布到-github-release)
- [用户安装指南](#用户安装指南)
- [付费支持](#付费支持)

---

## 打包流程

### 1. 环境准备

```bash
# 确保使用 Python 3.11（不支持 3.12）
pyenv local 3.11.15

# 激活虚拟环境
source venv/bin/activate

# 安装打包依赖
pip install -r requirements-dev.txt
```

### 2. 版本管理

修改以下文件中的版本号（必须保持一致）：

- `setup.py` → `version='x.x.x'`
- `app_menubar.py` → `__version__ = 'x.x.x'`
- `aigard/updater.py` → `CURRENT_VERSION = 'x.x.x'`

**自动检查：** `build.sh` 会自动调用 `scripts/check-version.sh` 检查版本一致性

### 3. 执行打包

```bash
# 一键打包（自动版本检查）
./build.sh

# 输出：dist/AI Guard.app
```

---

## 签名与公证

### 前置条件

1. **Apple Developer 账号**（付费，$99/年）
2. **Developer ID Application 证书**
   - 在 Xcode → Settings → Accounts → Manage Certificates 中创建
   - 或在 [Apple Developer](https://developer.apple.com/account/resources/certificates/list) 网站创建

3. **App-Specific Password**（用于公证）
   ```bash
   # 在 Apple ID 网站生成：https://appleid.apple.com/account/manage
   # 存储到 Keychain（只需执行一次）
   xcrun notarytool store-credentials "notarytool-profile" \
     --apple-id "your-email@example.com" \
     --team-id "YOUR_TEAM_ID" \
     --password "xxxx-xxxx-xxxx-xxxx"
   ```

### 签名流程

```bash
cd "/path/to/AI Guard"

# 1. 查找你的 Developer ID 证书
security find-identity -v -p codesigning

# 2. 签名所有二进制文件（从内到外）
DEVELOPER_ID="Developer ID Application: Your Name (TEAM_ID)"

# 签名所有 .so/.dylib 文件
find "dist/AI Guard.app" -type f \( -name "*.so" -o -name "*.dylib" \) | while read file; do
  codesign --force --sign "$DEVELOPER_ID" \
    --timestamp \
    --options runtime \
    "$file"
done

# 签名 Python 可执行文件
codesign --force --sign "$DEVELOPER_ID" \
  --timestamp \
  --options runtime \
  "dist/AI Guard.app/Contents/MacOS/python"

# 签名整个 .app（必须最后签名）
codesign --force --sign "$DEVELOPER_ID" \
  --timestamp \
  --options runtime \
  --entitlements entitlements.plist \
  "dist/AI Guard.app"

# 3. 验证签名
codesign --verify --deep --strict --verbose=2 "dist/AI Guard.app"
spctl --assess --type execute --verbose=2 "dist/AI Guard.app"
```

### 公证流程

```bash
cd dist

# 1. 打包成 ZIP
ditto -c -k --keepParent "AI Guard.app" "AI Guard.zip"

# 2. 提交公证（使用之前存储的凭证）
xcrun notarytool submit "AI Guard.zip" \
  --keychain-profile "notarytool-profile" \
  --wait

# 3. 钉上公证票据（让用户离线安装时也能验证）
xcrun stapler staple "AI Guard.app"

# 4. 验证票据
xcrun stapler validate "AI Guard.app"
```

### 制作 DMG 安装包

```bash
# 创建 DMG（包含 .app 和 Applications 快捷方式）
hdiutil create -volname "AI Guard" \
  -srcfolder "dist/AI Guard.app" \
  -ov -format UDZO \
  "dist/AI-Guard-v1.1.3.dmg"
```

---

## 发布到 GitHub Release

### 方式一：使用 GitHub CLI（推荐）

```bash
# 1. 创建 Git Tag
git tag -a v1.1.3 -m "Release v1.1.3"
git push origin v1.1.3

# 2. 创建 Release 并上传 DMG
gh release create v1.1.3 \
  "dist/AI-Guard-v1.1.3.dmg" \
  --title "AI Guard v1.1.3" \
  --notes "$(cat <<'EOF'
## 新功能
- ✨ 菜单栏状态显示优化
- 📊 Claude 使用统计自动缓存重建

## 修复
- 🐛 修复缓存数据不完整问题

## 安装方式
1. 下载 `AI-Guard-v1.1.3.dmg`
2. 双击打开，拖拽到 Applications 文件夹
3. 首次启动需要在"系统设置 → 隐私与安全性"中允许运行

---

**支持开发：** 如果这个工具帮到了你，欢迎[打赏支持](https://github.com/sponsors/your-username) ☕
EOF
)"
```

### 方式二：手动上传

1. 访问 https://github.com/your-username/ai-guard/releases/new
2. 填写 Tag version: `v1.1.3`
3. 填写 Release title: `AI Guard v1.1.3`
4. 上传 `dist/AI-Guard-v1.1.3.dmg`
5. 填写 Release notes（参考上面的模板）
6. 点击 "Publish release"

---

## 用户安装指南

### 下载与安装

1. 访问 [Releases 页面](https://github.com/your-username/ai-guard/releases)
2. 下载最新版本的 `.dmg` 文件
3. 双击 DMG，拖拽 "AI Guard" 到 "Applications" 文件夹
4. 打开 "应用程序" 文件夹，双击 "AI Guard"

### 首次启动

macOS 可能会提示"无法打开，因为无法验证开发者"：

1. 打开"系统设置 → 隐私与安全性"
2. 找到 "AI Guard" 的提示，点击"仍要打开"
3. 再次双击 "AI Guard" 即可启动

**注意：** 如果应用已通过 Apple 公证，不会出现此提示。

### 开机自启（可选）

```bash
# 下载并运行安装脚本
curl -fsSL https://raw.githubusercontent.com/your-username/ai-guard/main/scripts/install_autostart.sh | bash
```

或手动安装：

```bash
cd /Applications/AI\ Guard.app/Contents/Resources
bash scripts/install_autostart.sh
```

---

## 付费支持

AI Guard 是 **100% 开源免费软件**（MIT 协议），所有功能完全免费使用，无任何限制。

打赏是**完全自愿**的，不影响软件的任何功能。如果这个工具帮到了你，欢迎 **¥6 元打赏支持**（一杯奶茶的价格），用于：
- ☕ 支持开发者持续维护
- 🐛 更快响应 Bug 修复
- ✨ 开发更多实用功能

**开发者：** 小力创意文化产业发展（北京）有限公司  
**开源协议：** MIT License  
**代码仓库：** https://github.com/Xaiver03/ai-guard

### 打赏方式

**建议金额：¥6 元** — 一杯奶茶的价格，支持开源开发 ☕

#### 1. 支付宝/微信打赏（推荐）

<details>
<summary>点击展开二维码</summary>

**支付宝：**

```
[放置支付宝收款码图片，建议设置默认金额 ¥6]
```

**微信支付：**

```
[放置微信收款码图片，建议设置默认金额 ¥6]
```

</details>

#### 2. 爱发电

访问 [爱发电主页](https://afdian.net/@your-username) 进行赞助，单次 ¥6 或设置月度支持。

#### 3. GitHub Sponsors

访问 [GitHub Sponsors](https://github.com/sponsors/your-username) 设置一次性打赏（约 $1）或月度赞助。

### 企业赞助

如果你的公司在使用 AI Guard，欢迎联系我讨论企业赞助方案：

- 📧 Email: your-email@example.com
- 💬 微信: your-wechat-id

---

## 常见问题

### Q: 为什么需要 Apple Developer 账号？

A: 没有 Developer ID 签名的应用会被 macOS Gatekeeper 拦截，用户需要手动绕过安全检查。公证后的应用可以直接安装，用户体验更好。

### Q: 可以不签名直接分发吗？

A: 可以，但用户需要：
1. 右键点击应用 → "打开"
2. 或在"系统设置 → 隐私与安全性"中手动允许

这会降低用户信任度和安装成功率。

### Q: 公证失败怎么办？

A: 常见原因：
1. **未签名的二进制文件** → 用 `find` 找到所有 `.so/.dylib` 并签名
2. **缺少时间戳** → 签名时加上 `--timestamp` 参数
3. **Hardened Runtime 问题** → 检查 `entitlements.plist` 配置

查看详细错误：
```bash
xcrun notarytool log <submission-id> --keychain-profile "notarytool-profile"
```

### Q: 如何更新已发布的版本？

A: 不要修改已发布的 Release，而是：
1. 修改版本号（如 v1.1.3 → v1.1.4）
2. 重新打包、签名、公证
3. 创建新的 Release

---

## 自动化脚本

完整的签名+公证+DMG 制作脚本：

```bash
#!/bin/bash
# scripts/notarize.sh

set -e

DEVELOPER_ID="Developer ID Application: Your Name (TEAM_ID)"
VERSION=$(grep "version=" setup.py | cut -d"'" -f2)
APP_PATH="dist/AI Guard.app"
DMG_PATH="dist/AI-Guard-v${VERSION}.dmg"

echo "=== 签名所有二进制文件 ==="
find "$APP_PATH" -type f \( -name "*.so" -o -name "*.dylib" \) | while read file; do
  codesign --force --sign "$DEVELOPER_ID" --timestamp --options runtime "$file"
done

codesign --force --sign "$DEVELOPER_ID" --timestamp --options runtime "$APP_PATH/Contents/MacOS/python"
codesign --force --sign "$DEVELOPER_ID" --timestamp --options runtime --entitlements entitlements.plist "$APP_PATH"

echo "=== 验证签名 ==="
codesign --verify --deep --strict --verbose=2 "$APP_PATH"

echo "=== 提交公证 ==="
cd dist
ditto -c -k --keepParent "AI Guard.app" "AI Guard.zip"
xcrun notarytool submit "AI Guard.zip" --keychain-profile "notarytool-profile" --wait

echo "=== 钉票据 ==="
xcrun stapler staple "$APP_PATH"
xcrun stapler validate "$APP_PATH"

echo "=== 制作 DMG ==="
hdiutil create -volname "AI Guard" -srcfolder "$APP_PATH" -ov -format UDZO "$DMG_PATH"

echo "✅ 完成！DMG 位置: $DMG_PATH"
```

使用方式：

```bash
chmod +x scripts/notarize.sh
./scripts/notarize.sh
```

---

## 参考资料

- [Apple 公证指南](https://developer.apple.com/documentation/security/notarizing_macos_software_before_distribution)
- [代码签名指南](https://developer.apple.com/library/archive/documentation/Security/Conceptual/CodeSigningGuide/Introduction/Introduction.html)
- [py2app 文档](https://py2app.readthedocs.io/)
