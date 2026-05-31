"""
# [CN] AI 驱动的书签分析器
# [CN] 使用 Claude API 分析书签并提供整理建议
"""

import json
import re
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
import httpx
from pathlib import Path

from .ai_config import get_ai_config
from .models import BookmarkData, Category


class BookmarkAnalyzer:
    # [CN] """AI 驱动的书签分析器"""

    def __init__(self, db_path: Optional[Path] = None):
        self.ai_config = get_ai_config()
        self.db_path = db_path or Path.home() / ".aigard" / "bookmarks.db"

    def analyze_bookmarks(self, bookmarks: List[BookmarkData]) -> Dict[str, Any]:
        """
        分析书签列表,识别问题

        Args:
            bookmarks: 书签对象列表

        Returns:
            分析结果字典
        """
        issues = {
            "duplicates": self._find_duplicates(bookmarks),
            "url_issues": self._find_url_issues(bookmarks),
            "naming_issues": self._find_naming_issues(bookmarks),
            "broken_links": self._find_broken_links(bookmarks),
            "uncategorized": self._find_uncategorized(bookmarks)
        }

        return {
            "total_bookmarks": len(bookmarks),
            "issues": issues,
            "issue_count": sum(len(v) for v in issues.values() if isinstance(v, list))
        }

    def _find_duplicates(self, bookmarks: List[BookmarkData]) -> List[Dict[str, Any]]:
        # [CN] """查找重复的书签"""
        url_map = {}
        duplicates = []

        for bm in bookmarks:
            if not bm.url:
                continue

            # [CN] 标准化 URL(移除尾部斜杠、查询参数等)
            normalized_url = self._normalize_url(bm.url)

            if normalized_url in url_map:
                duplicates.append({
                    "id": bm.id,
                    "url": bm.url,
                    "title": bm.name,
                    "folder_id": bm.folder_id,
                    "duplicate_of": url_map[normalized_url]
                })
            else:
                url_map[normalized_url] = {
                    "id": bm.id,
                    "title": bm.name,
                    "folder_id": bm.folder_id
                }

        return duplicates

    def _normalize_url(self, url: str) -> str:
        # [CN] """标准化 URL 用于比较"""
        try:
            parsed = urlparse(url)
            # [CN] # 移除尾部斜杠
            path = parsed.path.rstrip('/')
            # [CN] # 移除常见的追踪参数
            query_params = parse_qs(parsed.query)
            tracking_params = ['utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term', 'ref', 'source']
            for param in tracking_params:
                query_params.pop(param, None)

            new_query = urlencode(query_params, doseq=True)
            return urlunparse((parsed.scheme, parsed.netloc, path, '', new_query, ''))
        except:
            return url

    def _find_url_issues(self, bookmarks: List[BookmarkData]) -> List[Dict[str, Any]]:
        # [CN] """查找 URL 问题(追踪参数、过长等)"""
        issues = []

        for bm in bookmarks:
            if not bm.url:
                continue

            problems = []

            # [CN] 检查追踪参数
            if any(param in bm.url for param in ['utm_', 'ref=', 'source=']):
                problems.append("包含追踪参数")

            # Check URL Length
            if len(bm.url) > 200:
                problems.append(f"URL 过长 ({len(bm.url)} 字符)")

            # [CN] 检查是否是重定向链接
            if 'redirect' in bm.url.lower() or 'link.zhihu.com' in bm.url or 'link.juejin.cn' in bm.url:
                problems.append("可能是重定向链接")

            if problems:
                issues.append({
                    "id": bm.id,
                    "url": bm.url,
                    "title": bm.title,
                    "category_id": bm.category_id,
                    "problems": problems
                })

        return issues

    def _find_naming_issues(self, bookmarks: List[BookmarkData]) -> List[Dict[str, Any]]:
        # [CN] """查找命名问题"""
        issues = []

        for bm in bookmarks:
            problems = []

            # 名称过长
            if len(bm.title) > 50:
                problems.append(f"名称过长 ({len(bm.title)} 字符)")

            # 使用 URL 作为名称
            if bm.title == bm.url or bm.title.startswith('http'):
                problems.append("使用 URL 作为名称")

            # 包含特殊字符
            if re.search(r'[<>:"/\\|?*]', bm.title):
                problems.append("包含特殊字符")

            # 名称为空
            if not bm.title or bm.title.strip() == "":
                problems.append("名称为空")

            if problems:
                issues.append({
                    "id": bm.id,
                    "title": bm.title,
                    "url": bm.url,
                    "category_id": bm.category_id,
                    "problems": problems
                })

        return issues

    def _find_broken_links(self, bookmarks: List[BookmarkData]) -> List[Dict[str, Any]]:
        # [CN] """查找可能失效的链接"""
        broken = []

        for bm in bookmarks:
            # 检查是否有明显的失效标记
            if bm.metadata and bm.metadata.get("is_broken"):
                broken.append({
                    "id": bm.id,
                    "title": bm.title,
                    "url": bm.url,
                    "category_id": bm.category_id,
                    "reason": "标记为失效"
                })

        return broken

    def _find_large_folders(self, bookmarks: List[BookmarkData]) -> List[Dict[str, Any]]:
        # [CN] """查找过大的分类"""
        category_counts = {}

        for bm in bookmarks:
            category_id = bm.category_id or "未分类"
            category_counts[category_id] = category_counts.get(category_id, 0) + 1

        # [CN] 超过 20 个书签的分类
        large_categories = [
            {"category_id": category_id, "count": count}
            for category_id, count in category_counts.items()
            if count > 20
        ]

        return sorted(large_categories, key=lambda x: x["count"], reverse=True)

    def _find_uncategorized(self, bookmarks: List[BookmarkData]) -> List[Dict[str, Any]]:
        """查找未分类的书签"""
        uncategorized = []

        for bm in bookmarks:
            if not bm.category_id:
                uncategorized.append({
                    "id": bm.id,
                    "title": bm.title,
                    "url": bm.url
                })

        return uncategorized

    async def ai_categorize_bookmarks(self, bookmarks: List[BookmarkData], max_bookmarks: int = 50) -> Dict[str, Any]:
        """
        使用 AI 对书签进行分类建议

        Args:
            bookmarks: 书签列表
            max_bookmarks: 最多分析的书签数量(避免 token 过多)

        Returns:
            AI 分类建议
        """
        if not self.ai_config.is_configured():
            return {
                "error": "AI 未配置",
                "message": "请确保 Claude Code 的 settings.json 中配置了 ANTHROPIC_AUTH_TOKEN"
            }

        # [CN] # 限制书签数量
        sample_bookmarks = bookmarks[:max_bookmarks]

        # [CN] # 构建提示词
        prompt = self._build_categorization_prompt(sample_bookmarks)

        try:
            # Invoke Claude API
            response = await self._call_claude_api(prompt)
            return self._parse_categorization_response(response)

        except Exception as e:
            return {
                "error": "AI InvokeFailure",
                "message": str(e)
            }

    def _build_categorization_prompt(self, bookmarks: List[Bookmark]) -> str:
        """构建分类提示词"""
        bookmark_list = []
        for i, bm in enumerate(bookmarks, 1):
            bookmark_list.append(f"{i}. {bm.title} - {bm.url}")

        bookmarks_text = "\n".join(bookmark_list)

        return f"""请分析以下书签,并提供分类建议。

书签列表:
{bookmarks_text}

请按照以下格式返回 JSON:
{{
  "categories": [
    {{
      "name": "分类名称",
      "description": "分类描述",
      "bookmarks": [1, 3, 5]
    }}
  ],
  "suggestions": [
    "建议1",
    "建议2"
  ]
}}

分类原则:
1. 按照主题和用途分类(如:开发工具、学习资源、新闻媒体等)
2. 每个分类不超过 20 个书签
3. 分类名称简洁明了
4. 提供具体的整理建议

只返回 JSON,不要其他内容。"""

    async def _call_claude_api(self, prompt: str) -> str:
        """Invoke Claude API"""
        endpoint = self.ai_config.get_api_endpoint()
        headers = self.ai_config.get_headers()

        payload = {
            "model": self.ai_config.model,
            "max_tokens": 4096,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(endpoint, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["content"][0]["text"]

    def _parse_categorization_response(self, response: str) -> Dict[str, Any]:
        # [CN] """解析 AI 返回的分类建议"""
        try:
            # [CN] 提取 JSON(可能包含在 markdown 代码块中)
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = response

            return json.loads(json_str)

        except Exception as e:
            return {
                "error": "解析失败",
                "message": str(e),
                "raw_response": response
            }

    async def ai_suggest_bookmark_name(self, url: str, current_name: str = "") -> str:
        """
        # [CN] 使用 AI 建议更好的书签名称

        Args:
            # [CN] url: 书签 URL
            # [CN] current_name: 当前名称

        Returns:
            # [CN] 建议的名称
        """
        if not self.ai_config.is_configured():
            return current_name

        prompt = f"""请为以下网址建议一个简洁、描述性的书签名称(不超过 30 个字符):

URL: {url}
当前名称: {current_name}

只返回建议的名称,不要其他内容。"""

        try:
            response = await self._call_claude_api(prompt)
            return response.strip()
        except:
            return current_name

    def clean_url(self, url: str) -> str:
        # [CN] """清理 URL(移除追踪参数)"""
        return self._normalize_url(url)
