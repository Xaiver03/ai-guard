#!/bin/bash
set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

echo "清理旧构建..."
rm -rf build dist

echo "开始 py2app 打包..."
python3 setup.py py2app

echo "自签名（避免 Gatekeeper 拦截）..."
codesign --force --deep --sign - "dist/AI Guard.app"

echo ""
echo "构建完成！"
echo "   App 路径：$PROJECT_DIR/dist/AI Guard.app"
echo "   运行：open \"$PROJECT_DIR/dist/AI Guard.app\""
