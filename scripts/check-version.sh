#!/bin/bash
# 版本一致性检查脚本
# 参考 Vibe Usage 的 check-version.sh
# 确保 setup.py 中 CFBundleVersion 和 CFBundleShortVersionString 一致，
# 且版本号大于最新 Git tag

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "🔍 检查版本一致性..."

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# 从 setup.py 的 plist 中提取 CFBundleVersion
BUNDLE_VERSION=$(grep '"CFBundleVersion"' "$PROJECT_ROOT/setup.py" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)

# 从 setup.py 的 plist 中提取 CFBundleShortVersionString
SHORT_VERSION=$(grep '"CFBundleShortVersionString"' "$PROJECT_ROOT/setup.py" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)

echo "📦 CFBundleVersion: ${BUNDLE_VERSION}"
echo "📦 CFBundleShortVersionString: ${SHORT_VERSION}"

ERRORS=0

# 检查版本格式
if ! [[ "$BUNDLE_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo -e "${RED}❌ CFBundleVersion 格式错误: $BUNDLE_VERSION${NC}"
    ERRORS=$((ERRORS + 1))
fi

if ! [[ "$SHORT_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo -e "${RED}❌ CFBundleShortVersionString 格式错误: $SHORT_VERSION${NC}"
    ERRORS=$((ERRORS + 1))
fi

# 检查两个版本号一致
if [ "$BUNDLE_VERSION" != "$SHORT_VERSION" ]; then
    echo -e "${RED}❌ 版本不一致: CFBundleVersion ($BUNDLE_VERSION) != CFBundleShortVersionString ($SHORT_VERSION)${NC}"
    ERRORS=$((ERRORS + 1))
fi

# 检查 README.md 中的版本引用
README_VERSION=$(grep -oE "AI-Guard-v[0-9]+\.[0-9]+\.[0-9]+" "$PROJECT_ROOT/README.md" 2>/dev/null | head -1 | sed 's/AI-Guard-v//' || echo "")
if [ -n "$README_VERSION" ] && [ "$README_VERSION" != "$BUNDLE_VERSION" ]; then
    echo -e "${YELLOW}⚠️  README.md 中的版本 ($README_VERSION) != setup.py ($BUNDLE_VERSION)${NC}"
fi

# 版本比较函数
version_gt() {
    test "$(printf '%s\n' "$@" | sort -V | head -n 1)" != "$1"
}

# 检查是否比最新 tag 更新
LATEST_TAG=$(cd "$PROJECT_ROOT" && git describe --tags --abbrev=0 2>/dev/null | sed 's/^v//' || echo "")
if [ -n "$LATEST_TAG" ]; then
    echo "🏷️  最新 Git tag: v${LATEST_TAG}"
    if ! version_gt "$BUNDLE_VERSION" "$LATEST_TAG" && [ "$BUNDLE_VERSION" != "$LATEST_TAG" ]; then
        echo -e "${RED}❌ 当前版本 ($BUNDLE_VERSION) 必须 >= 最新 tag ($LATEST_TAG)${NC}"
        ERRORS=$((ERRORS + 1))
    fi
else
    echo "🏷️  未找到 Git tag（首次发布）"
fi

if [ $ERRORS -gt 0 ]; then
    echo -e "\n${RED}❌ 发现 $ERRORS 个版本错误，请修复后再打包${NC}"
    exit 1
fi

echo -e "${GREEN}✅ 版本检查通过: v${BUNDLE_VERSION}${NC}"
exit 0
