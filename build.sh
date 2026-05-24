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
python3 setup.py py2app

echo "🔏 步骤 4: 自签名（避免 Gatekeeper 拦截）..."
codesign --force --deep --sign - "dist/AI Guard.app"

echo ""
echo "✅ 构建完成！"
echo "   App 路径：$PROJECT_DIR/dist/AI Guard.app"
echo ""
echo "📋 下一步："
echo "   安装: cp -r \"dist/AI Guard.app\" /Applications/"
echo "   运行: open \"/Applications/AI Guard.app\""
