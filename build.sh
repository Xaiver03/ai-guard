#!/bin/bash
set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

echo "🔍 步骤 1: 版本检查..."
bash scripts/check-version.sh || exit 1
echo ""

echo "🗑️  步骤 2: 清理旧构建..."
rm -rf build dist

echo "📦 步骤 3: py2app 打包..."
source venv/bin/activate
python setup.py py2app

echo "🔏 步骤 4: 开发者签名（解决权限重置问题）..."
SIGNING_IDENTITY="Developer ID Application: Xiaoli Creativity Culture Industry Development (beijing) Co., Ltd. (V5S2LT9YV8)"
codesign --force --deep --sign "$SIGNING_IDENTITY" \
  --options runtime \
  --entitlements entitlements.plist \
  "dist/AI Guard.app"

echo "✅ 验证签名..."
codesign -dv --verbose=4 "dist/AI Guard.app" 2>&1 | grep -E "(Signature|Identifier|TeamIdentifier)"

echo ""
echo "✅ 构建完成！"
echo "   App 路径：$PROJECT_DIR/dist/AI Guard.app"
echo ""
echo "📋 下一步："
echo "   安装: cp -r \"dist/AI Guard.app\" /Applications/"
echo "   运行: open \"/Applications/AI Guard.app\""
