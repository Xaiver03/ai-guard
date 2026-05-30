"""
# [CN] AI 驱动的书签分析器
# [CN] 使用 Claude API 分析书签并提供整理建议
"""

import json
import re
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
import httpx

from .ai_config import get_ai_config


class BookmarkAnalyzer:
    # [CN] """AI 驱动的书签分析器"""

    def __init__(self):
        self.ai_config = get_ai_config()

    def analyze_bookmarks(self, bookmarks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        分析书签列表，识别问题

        Args:
            bookmarks: 书签列表

        Returns:
            分析结果字典
        """
        issues = {
            "duplicates": self._find_duplicates(bookmarks),
            "url_issues": self._find_url_issues(bookmarks),
            "naming_issues": self._find_naming_issues(bookmarks),
            "large_folders": self._find_large_folders(bookmarks),
            "uncategorized": self._find_uncategorized(bookmarks)
        }

        return {
            "total_bookmarks": len(bookmarks),
            "issues": issues,
            "issue_count": sum(len(v) for v in issues.values() if isinstance(v, list))
        }

    def _find_duplicates(self, bookmarks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        # [CN] """查找重复的书签"""
        url_map = {}
        duplicates = []

        for bm in bookmarks:
            url = bm.get("url", "")
            if not url:
                continue

            # [CN] 标准化 URL（移除尾部斜杠、查询参数等）
            normalized_url = self._normalize_url(url)

            if normalized_url in url_map:
                duplicates.append({
                    "url": url,
                    "name": bm.get("name", ""),
                    "folder": bm.get("folder", ""),
                    "duplicate_of": url_map[normalized_url]
                })
            else:
                url_map[normalized_url] = {
                    "name": bm.get("name", ""),
                    "folder": bm.get("folder", "")
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

    def _find_url_issues(self, bookmarks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        # [CN] """查找 URL 问题（追踪参数、过长等）"""
        issues = []

        for bm in bookmarks:
            url = bm.get("url", "")
            if not url:
                continue

            problems = []

            # [CN] 检查追踪参数
            if any(param in url for param in ['utm_', 'ref=', 'source=']):
                problems.append("包含追踪参数")

            # Check URL Length
            if len(url) > 200:
                problems.append(f"URL 过长 ({len(url)} 字符)")

            # [CN] 检查是否是重定向链接
            if 'redirect' in url.lower() or 'link.zhihu.com' in url or 'link.juejin.cn' in url:
                problems.append("可能是重定向链接")

            if problems:
                issues.append({
                    "url": url,
                    "name": bm.get("name", ""),
                    "folder": bm.get("folder", ""),
                    "problems": problems
                })

        return issues

    def _find_naming_issues(self, bookmarks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        # [CN] """查找命名问题"""
        issues = []

        for bm in bookmarks:
            name = bm.get("name", "")
            url = bm.get("url", "")

            problems = []

            # [CN] # 名称过长
            if len(name) > 50:
                # [CN] problems.append(f"名称过长 ({len(name)} 字符)")

            # [CN] # 使用 URL 作为名称
            if name == url or name.startswith('http'):
                # [CN] problems.append("使用 URL 作为名称")

            # [CN] # 包含特殊字符
            if re.search(r'[<>:"/\\|?*]', name):
                # [CN] problems.append("包含特殊字符")

            # [CN] # 名称为空
            if not name or name.strip() == "":
                # [CN] problems.append("名称为空")

            if problems:
                issues.append({
                    "name": name,
                    "url": url,
                    "folder": bm.get("folder", ""),
                    "problems": problems
                })

        return issues

    def _find_large_folders(self, bookmarks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        # [CN] """查找过大的文件夹"""
        folder_counts = {}

        for bm in bookmarks:
            folder = bm.get("folder", "未分类")
            folder_counts[folder] = folder_counts.get(folder, 0) + 1

        # [CN] 超过 20 个书签的文件夹
        large_folders = [
            {"folder": folder, "count": count}
            for folder, count in folder_counts.items()
            if count > 20
        ]

        return sorted(large_folders, key=lambda x: x["count"], reverse=True)

    def _find_uncategorized(self, bookmarks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        # [CN] """查找未分类的书签"""
        uncategorized = []

        for bm in bookmarks:
            folder = bm.get("folder", "")
            # [CN] if not folder or folder in ["未分类", "其他书签", "Other Bookmarks"]:
                uncategorized.append({
                    "name": bm.get("name", ""),
                    "url": bm.get("url", ""),
                    "folder": folder
                })

        return uncategorized

    async def ai_categorize_bookmarks(self, bookmarks: List[Dict[str, Any]], max_bookmarks: int = 50) -> Dict[str, Any]:
        """
        使用 AI 对书签进行分类建议

        Args:
            bookmarks: 书签列表
            max_bookmarks: 最多分析的书签数量（避免 token 过多）

        Returns:
            AI 分类建议
        """
        if not self.ai_config.is_configured():
            return {
                # [CN] "error": "AI 未配置",
                # [CN] "message": "请确保 Claude Code 的 settings.json 中配置了 ANTHROPIC_AUTH_TOKEN"
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

    def _build_categorization_prompt(self, bookmarks: List[Dict[str, Any]]) -> str:
        # [CN] """构建分类提示词"""
        bookmark_list = []
        for i, bm in enumerate(bookmarks, 1):
            bookmark_list.append(f"{i}. {bm.get('name', '')} - {bm.get('url', '')}")

        bookmarks_text = "\n".join(bookmark_list)

        # [CN] return f"""请分析以下书签，并提供分类建议。

# [CN] 书签列表：
{bookmarks_text}

# [CN] 请按照以下格式返回 JSON：
{{
  "categories": [
    {{
      # [CN] "name": "分类名称",
      # [CN] "description": "分类描述",
      # [CN] "bookmarks": [1, 3, 5]  // 书签编号列表
    }}
  ],
  "suggestions": [
    # [CN] "建议1",
    # [CN] "建议2"
  ]
}}

# [CN] 分类原则：
# [CN] 1. 按照主题和用途分类（如：开发工具、学习资源、新闻媒体等）
# [CN] 2. 每个分类不超过 20 个书签
# [CN] 3. 分类名称简洁明了
# [CN] 4. 提供具体的整理建议

# [CN] 只返回 JSON，不要其他内容。"""

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
            # [CN] 提取 JSON（可能包含在 markdown 代码块中）
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

        # [CN] prompt = f"""请为以下网址建议一个简洁、描述性的书签名称（不超过 30 个字符）：

URL: {url}
# [CN] 当前名称: {current_name}

# [CN] 只返回建议的名称，不要其他内容。"""

        try:
            response = await self._call_claude_api(prompt)
            return response.strip()
        except:
            return current_name

    def clean_url(self, url: str) -> str:
        # [CN] """清理 URL（移除追踪参数）"""
        return self._normalize_url(url)
