"""
# [CN] 书签管理器核心类
# [CN] 支持多浏览器书签的读取、分析和管理
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime


class BookmarkManager:
    """浏览器书签管理器"""

    # 支持的浏览器及其书签文件路径
    BROWSER_PATHS = {
        "chrome": "~/Library/Application Support/Google/Chrome/Default/Bookmarks",
        "edge": "~/Library/Application Support/Microsoft Edge/Default/Bookmarks",
        "dia": "~/Library/Application Support/Dia/User Data/Default/Bookmarks",
        "quark": "~/Library/Application Support/Quark/Default/Bookmarks",
        "safari": "~/Library/Safari/Bookmarks.plist",
    }

    def __init__(self):
        self.bookmarks_cache: Dict[str, Any] = {}
        self.detected_browsers: List[str] = []
        self._detect_browsers()

    def _detect_browsers(self):
        """检测系统中已安装的浏览器"""
        for browser, path_str in self.BROWSER_PATHS.items():
            path = Path(path_str).expanduser()
            if path.exists():
                self.detected_browsers.append(browser)

    def get_detected_browsers(self) -> List[Dict[str, Any]]:
        """获取检测到的浏览器列表"""
        result = []
        for browser in self.detected_browsers:
            path = Path(self.BROWSER_PATHS[browser]).expanduser()
            result.append({
                "name": browser,
                "display_name": self._get_browser_display_name(browser),
                "path": str(path),
                "type": "plist" if browser == "safari" else "chromium"
            })
        return result

    def _get_browser_display_name(self, browser: str) -> str:
        """获取浏览器显示名称"""
        names = {
            "chrome": "Google Chrome",
            "edge": "Microsoft Edge",
            "dia": "DIA Browser",
            "quark": "Quark Browser",
            "safari": "Safari"
        }
        return names.get(browser, browser.title())

    def read_bookmarks(self, browser: str, force_reload: bool = False) -> Optional[Dict[str, Any]]:
        """
        读取指定浏览器的书签

        Args:
            browser: 浏览器名称 (chrome, edge, dia, quark, safari)
            force_reload: 是否强制重新加载

        Returns:
            书签数据字典,如果失败返回 None
        """
        if browser not in self.detected_browsers:
            return None

        # 使用缓存
        if not force_reload and browser in self.bookmarks_cache:
            return self.bookmarks_cache[browser]

        path = Path(self.BROWSER_PATHS[browser]).expanduser()

        try:
            if browser == "safari":
                # Safari 使用 plist 格式
                from .safari import SafariBookmarkReader
                reader = SafariBookmarkReader()
                data = reader.read(path)
            else:
                # Chromium 内核浏览器使用 JSON 格式
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

            self.bookmarks_cache[browser] = data
            return data

        except Exception as e:
            print(f"读取 {browser} 书签失败: {e}")
            return None

    def extract_all_bookmarks(self, browser: str) -> List[Dict[str, Any]]:
        """
        提取所有书签为扁平列表

        Args:
            browser: 浏览器名称

        Returns:
            书签列表,每个书签包含 name, url, folder, date_added 等字段
        """
        data = self.read_bookmarks(browser)
        if not data:
            return []

        if browser == "safari":
            return self._extract_safari_bookmarks(data)
        else:
            return self._extract_chromium_bookmarks(data)

    def _extract_chromium_bookmarks(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """提取 Chromium 内核浏览器的书签"""
        bookmarks = []

        def traverse(node, folder_path=""):
            if node.get("type") == "url":
                bookmarks.append({
                    "name": node.get("name", ""),
                    "url": node.get("url", ""),
                    "folder": folder_path,
                    "date_added": node.get("date_added", ""),
                    "guid": node.get("guid", ""),
                    "id": node.get("id", "")
                })
            elif node.get("type") == "folder":
                folder_name = node.get("name", "")
                new_path = f"{folder_path}/{folder_name}" if folder_path else folder_name
                for child in node.get("children", []):
                    traverse(child, new_path)

        # 遍历所有根节点
        roots = data.get("roots", {})
        for root_name, root_node in roots.items():
            if isinstance(root_node, dict) and "children" in root_node:
                display_name = self._get_root_display_name(root_name)
                for child in root_node.get("children", []):
                    traverse(child, display_name)

        return bookmarks

    def _extract_safari_bookmarks(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """提取 Safari 书签"""
        # Safari 书签提取逻辑由 SafariBookmarkReader 处理
        from .safari import SafariBookmarkReader
        reader = SafariBookmarkReader()
        return reader.extract_bookmarks(data)

    def _get_root_display_name(self, root_name: str) -> str:
        """获取根节点的显示名称"""
        names = {
            "bookmark_bar": "书签栏",
            "other": "其他书签",
            "synced": "移动设备书签"
        }
        return names.get(root_name, root_name)

    def get_bookmark_stats(self, browser: str) -> Dict[str, Any]:
        """
        获取书签统计信息

        Args:
            browser: 浏览器名称

        Returns:
            统计信息字典
        """
        bookmarks = self.extract_all_bookmarks(browser)

        if not bookmarks:
            return {
                "total": 0,
                "folders": {},
                "domains": {}
            }

        # 统计文件夹
        folders = {}
        domains = {}

        for bm in bookmarks:
            # 统计文件夹
            folder = bm.get("folder", "未分类")
            folders[folder] = folders.get(folder, 0) + 1

            # 统计域名
            url = bm.get("url", "")
            if url:
                try:
                    from urllib.parse import urlparse
                    domain = urlparse(url).netloc
                    if domain:
                        domains[domain] = domains.get(domain, 0) + 1
                except:
                    pass

        return {
            "total": len(bookmarks),
            "folders": folders,
            "domains": domains,
            "top_folders": sorted(folders.items(), key=lambda x: x[1], reverse=True)[:10],
            "top_domains": sorted(domains.items(), key=lambda x: x[1], reverse=True)[:10]
        }

    def search_bookmarks(self, browser: str, query: str) -> List[Dict[str, Any]]:
        """
        搜索书签

        Args:
            browser: 浏览器名称
            query: 搜索关键词

        Returns:
            匹配的书签列表
        """
        bookmarks = self.extract_all_bookmarks(browser)
        query_lower = query.lower()

        results = []
        for bm in bookmarks:
            name = bm.get("name", "").lower()
            url = bm.get("url", "").lower()
            folder = bm.get("folder", "").lower()

            if query_lower in name or query_lower in url or query_lower in folder:
                results.append(bm)

        return results

    def export_bookmarks(self, browser: str, output_path: str, format: str = "json"):
        """
        导出书签

        Args:
            browser: 浏览器名称
            output_path: 输出文件路径
            format: 导出格式 (json, html, csv)
        """
        bookmarks = self.extract_all_bookmarks(browser)

        if format == "json":
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(bookmarks, f, ensure_ascii=False, indent=2)

        elif format == "html":
            self._export_html(bookmarks, output_path)

        elif format == "csv":
            self._export_csv(bookmarks, output_path)

    def _export_html(self, bookmarks: List[Dict[str, Any]], output_path: str):
        """导出为 HTML 格式"""
        html = ['<!DOCTYPE NETSCAPE-Bookmark-file-1>']
        html.append('<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">')
        html.append('<TITLE>Bookmarks</TITLE>')
        html.append('<H1>Bookmarks</H1>')
        html.append('<DL><p>')

        # 按文件夹分组
        folders = {}
        for bm in bookmarks:
            folder = bm.get("folder", "未分类")
            if folder not in folders:
                folders[folder] = []
            folders[folder].append(bm)

        for folder, items in folders.items():
            html.append(f'    <DT><H3>{folder}</H3>')
            html.append('    <DL><p>')
            for bm in items:
                name = bm.get("name", "")
                url = bm.get("url", "")
                html.append(f'        <DT><A HREF="{url}">{name}</A>')
            html.append('    </DL><p>')

        html.append('</DL><p>')

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(html))

    def _export_csv(self, bookmarks: List[Dict[str, Any]], output_path: str):
        """导出为 CSV 格式"""
        import csv

        with open(output_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=["name", "url", "folder", "date_added"])
            writer.writeheader()
            for bm in bookmarks:
                writer.writerow({
                    "name": bm.get("name", ""),
                    "url": bm.get("url", ""),
                    "folder": bm.get("folder", ""),
                    "date_added": bm.get("date_added", "")
                })
