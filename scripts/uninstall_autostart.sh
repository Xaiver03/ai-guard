#!/bin/bash

PLIST_DST="$HOME/Library/LaunchAgents/com.aigard.menubar.plist"

if [ ! -f "$PLIST_DST" ]; then
    echo "ℹ️  未找到 LaunchAgent，无需卸载"
    exit 0
fi

echo "🔄 卸载 LaunchAgent..."
launchctl unload "$PLIST_DST" 2>/dev/null || true
rm "$PLIST_DST"
echo "✅ 开机自启已移除"
