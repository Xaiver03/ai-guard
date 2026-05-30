"""
# [CN] Safari 书签读取器
# [CN] 处理 Safari 的 plist 格式书签
"""

import plistlib
from pathlib import Path
from typing import Dict, List, Any, Optional


class SafariBookmarkReader:
    # [CN] """Safari 书签读取器"""

    def read(self, path: Path) -> Optional[Dict[str, Any]]:
        """
        读取 Safari 书签文件

        Args:
            path: 书签文件路径

        Returns:
            书签数据字典，如果失败返回 None
        """
        try:
            with open(path, 'rb') as f:
                return plistlib.load(f)
        except PermissionError:
            # [CN] print(f"权限不足，无法读取 Safari 书签: {path}")
            # [CN] print("提示：需要在「系统设置 > 隐私与安全性 > 完全磁盘访问权限」中授权")
            return None
        except Exception as e:
            # [CN] print(f"读取 Safari 书签失败: {e}")
            return None

    def extract_bookmarks(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        从 Safari plist 数据中提取书签

        Args:
            data: plist 数据字典

        Returns:
            书签列表
        """
        bookmarks = []

        def traverse(node, folder_path=""):
            # [CN] """递归遍历书签树"""
            if not isinstance(node, dict):
                return

            # [CN] 检查节点类型
            node_type = node.get("WebBookmarkType", "")

            if node_type == "WebBookmarkTypeLeaf":
                # [CN] 这是一个书签
                url_string = node.get("URLString", "")
                if url_string:
                    bookmarks.append({
                        "name": node.get("URIDictionary", {}).get("title", "") or url_string,
                        "url": url_string,
                        "folder": folder_path,
                        "date_added": "",
                        "guid": node.get("WebBookmarkUUID", ""),
                        "id": node.get("WebBookmarkUUID", "")
                    })

            elif node_type == "WebBookmarkTypeList":
                # [CN] 这是一个文件夹
                folder_name = node.get("Title", "")
                new_path = f"{folder_path}/{folder_name}" if folder_path else folder_name

                # [CN] 遍历子节点
                children = node.get("Children", [])
                for child in children:
                    traverse(child, new_path)

        # [CN] 从根节点开始遍历
        if "Children" in data:
            for child in data["Children"]:
                traverse(child, "")

        return bookmarks

    def get_bookmark_count(self, data: Dict[str, Any]) -> int:
        """
        # [CN] 获取书签总数

        Args:
            data: plist DataDictionary

        Returns:
            # [CN] 书签数量
        """
        count = 0

        def count_bookmarks(node):
            nonlocal count
            if not isinstance(node, dict):
                return

            node_type = node.get("WebBookmarkType", "")
            if node_type == "WebBookmarkTypeLeaf":
                url_string = node.get("URLString", "")
                if url_string:
                    count += 1

            elif node_type == "WebBookmarkTypeList":
                children = node.get("Children", [])
                for child in children:
                    count_bookmarks(child)

        if "Children" in data:
            for child in data["Children"]:
                count_bookmarks(child)

        return count
