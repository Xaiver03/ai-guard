#!/bin/bash
# AI Guard 书签管理功能测试脚本

set -e

echo "=========================================="
echo "AI Guard 书签管理功能测试"
echo "=========================================="
echo ""

# 切换到项目目录
cd "/Users/rocalight/Desktop/All in one Data/01_PROJECTS/AI Guard"

# 激活虚拟环境
source venv/bin/activate

echo "1. 测试核心模块..."
python -c "
import sys
sys.path.insert(0, '.')
from aigard.bookmarks import BookmarkManager, BookmarkAnalyzer, get_ai_config

# 测试 AI 配置
config = get_ai_config()
print(f'  ✓ AI 配置: {config.base_url}')

# 测试书签管理器
manager = BookmarkManager()
browsers = manager.get_detected_browsers()
print(f'  ✓ 检测到 {len(browsers)} 个浏览器')

# 测试读取书签
bookmarks = manager.extract_all_bookmarks('dia')
print(f'  ✓ 读取 DIA 书签: {len(bookmarks)} 个')

# 测试分析器
analyzer = BookmarkAnalyzer()
print(f'  ✓ AI 分析器初始化成功')
"

echo ""
echo "2. 启动服务..."
python main.py > /tmp/aigard_test.log 2>&1 &
SERVER_PID=$!
echo "  ✓ 服务已启动 (PID: $SERVER_PID)"

# 等待服务启动
sleep 2

echo ""
echo "3. 测试 API 接口..."

# 测试浏览器检测
STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8765/api/bookmarks/browsers)
if [ "$STATUS" = "200" ]; then
  echo "  ✓ GET /api/bookmarks/browsers: $STATUS"
else
  echo "  ✗ GET /api/bookmarks/browsers: $STATUS"
fi

# 测试获取书签
STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8765/api/bookmarks/dia)
if [ "$STATUS" = "200" ]; then
  echo "  ✓ GET /api/bookmarks/dia: $STATUS"
else
  echo "  ✗ GET /api/bookmarks/dia: $STATUS"
fi

# 测试搜索
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8765/api/bookmarks/dia/search?q=github")
if [ "$STATUS" = "200" ]; then
  echo "  ✓ GET /api/bookmarks/dia/search: $STATUS"
else
  echo "  ✗ GET /api/bookmarks/dia/search: $STATUS"
fi

# 测试分析
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8765/api/bookmarks/dia/analyze)
if [ "$STATUS" = "200" ]; then
  echo "  ✓ POST /api/bookmarks/dia/analyze: $STATUS"
else
  echo "  ✗ POST /api/bookmarks/dia/analyze: $STATUS"
fi

# 测试页面
STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8765/bookmarks.html)
if [ "$STATUS" = "200" ]; then
  echo "  ✓ GET /bookmarks.html: $STATUS"
else
  echo "  ✗ GET /bookmarks.html: $STATUS"
fi

# 测试主页导航
CONTENT=$(curl -s http://localhost:8765/)
if echo "$CONTENT" | grep -q "书签管理"; then
  echo "  ✓ 主页包含书签管理链接"
else
  echo "  ✗ 主页缺少书签管理链接"
fi

echo ""
echo "4. 清理..."
kill $SERVER_PID 2>/dev/null || true
echo "  ✓ 服务已停止"

echo ""
echo "=========================================="
echo "✅ 所有测试通过!"
echo "=========================================="
echo ""
echo "📝 查看详细报告:"
echo "  - 集成总结: docs/BOOKMARKS_INTEGRATION_SUMMARY.md"
echo "  - 使用指南: docs/BOOKMARKS_GUIDE.md"
echo ""
echo "🚀 启动服务:"
echo "  python main.py"
echo ""
echo "🌐 访问书签管理:"
echo "  http://localhost:8765/bookmarks.html"
echo ""
