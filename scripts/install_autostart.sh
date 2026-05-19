#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
APP_BINARY="$PROJECT_DIR/dist/AI Guard.app/Contents/MacOS/AI Guard"
PLIST_SRC="$SCRIPT_DIR/com.aigard.menubar.plist"
PLIST_DST="$HOME/Library/LaunchAgents/com.aigard.menubar.plist"

if [ ! -f "$APP_BINARY" ]; then
    echo "❌ 找不到 App 可执行文件：$APP_BINARY"
    echo "   请先运行 bash build.sh 完成打包"
    exit 1
fi

echo "📝 写入 LaunchAgent plist..."
mkdir -p "$HOME/Library/LaunchAgents"
sed "s|PLACEHOLDER_APP_PATH|$APP_BINARY|g" "$PLIST_SRC" > "$PLIST_DST"

# 如果已有旧的 plist，先卸载再重装
launchctl unload "$PLIST_DST" 2>/dev/null || true
launchctl load "$PLIST_DST"

echo "✅ 开机自启已配置！"
echo "   下次登录时 AI Guard 将自动出现在菜单栏。"
echo ""
echo "   立即启动：launchctl start com.aigard.menubar"
echo "   停用自启：bash $SCRIPT_DIR/uninstall_autostart.sh"
