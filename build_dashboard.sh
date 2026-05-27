#!/bin/bash
# build_dashboard.sh — 打包监控面板独立应用

set -e

echo "🚀 开始打包 AI Guard Dashboard..."

# 步骤 1: 清理旧构建
echo "🧹 步骤 1: 清理旧构建..."
rm -rf build dist_dashboard
mkdir -p dist_dashboard

# 步骤 2: 运行 py2app
echo "📦 步骤 2: 运行 py2app..."
python setup_dashboard.py py2app --dist-dir dist_dashboard

# 步骤 3: 自签名
echo "🔏 步骤 3: 自签名..."
codesign --force --deep --sign - "dist_dashboard/AI Guard Dashboard.app"

echo ""
echo "✅ 构建完成！"
echo "   App 路径：$(pwd)/dist_dashboard/AI Guard Dashboard.app"
echo ""
echo "📋 下一步："
echo "   安装: cp -r \"dist_dashboard/AI Guard Dashboard.app\" /Applications/"
echo "   运行: open \"/Applications/AI Guard Dashboard.app\""
