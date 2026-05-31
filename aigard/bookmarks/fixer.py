"""
# [CN] 一键修复功能
# [CN] 提供智能去重、URL清理、批量重命名等功能
"""

from typing import Dict, List, Any, Optional
from collections import defaultdict
import re


class BookmarkFixer:
    """书签修复器"""

    def __init__(self):
        self.tracking_params = [
            'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
            'fbclid', 'gclid', 'msclkid', 'mc_cid', 'mc_eid',
            'ref', 'source', 'from', '_hsenc', '_hsmi',
            'spm_id_from', 'share_from', 'share_source',
            'sid', 'sessionid', 'session_id'
        ]

    def find_duplicates(self, bookmarks: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        查找重复书签

        Returns:
            重复书签组列表,每组包含多个重复项
        """
        url_map = defaultdict(list)

        def traverse(node, path=""):
            if node.get('type') == 'url':
                url = node.get('url', '')
                name = node.get('name', '')
                bookmark_id = node.get('id', '')

                url_map[url].append({
                    'id': bookmark_id,
                    'name': name,
                    'url': url,
                    'path': path
                })
            elif node.get('type') == 'folder':
                folder_name = node.get('name', '')
                new_path = f"{path} > {folder_name}" if path else folder_name

                for child in node.get('children', []):
                    traverse(child, new_path)

        roots = bookmarks.get('roots', {})
        for root_name in ['bookmark_bar', 'other', 'synced']:
            if root_name in roots:
                traverse(roots[root_name], root_name)

        # 只返回有重复的
        duplicates = []
        for url, items in url_map.items():
            if len(items) > 1:
                duplicates.append({
                    'url': url,
                    'count': len(items),
                    'items': items
                })

        return duplicates

    def smart_dedup_strategy(self, duplicate_group: Dict[str, Any]) -> Dict[str, Any]:
        """
        智能去重策略

        Returns:
            包含 keep_id 和 delete_ids 的字典
        """
        items = duplicate_group['items']

        # RatingRule
        def score_bookmark(item):
            score = 0
            path = item['path'].lower()

            # 在有意义文件夹中的加分
            if '未分类' not in path and 'other' not in path:
                score += 10

            # 在顶层文件夹的加分
            if path.count('>') <= 2:
                score += 5

            # 名称不是URL的加分
            if not item['name'].startswith('http'):
                score += 5

            # 名称不是 "Untitled" 的加分
            if item['name'].lower() != 'untitled':
                score += 3

            return score

        # 计算每个书签的分数
        scored_items = [(item, score_bookmark(item)) for item in items]
        scored_items.sort(key=lambda x: x[1], reverse=True)

        # 保留分数最高的
        keep_item = scored_items[0][0]
        delete_items = [item[0] for item in scored_items[1:]]

        return {
            'keep': keep_item,
            'delete': delete_items,
            'reason': f"保留在 '{keep_item['path']}' 中的书签(评分最高)"
        }

    def generate_dedup_operations(self, duplicates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        生成去重操作列表

        Returns:
            操作列表
        """
        operations = []

        for dup_group in duplicates:
            strategy = self.smart_dedup_strategy(dup_group)

            for item in strategy['delete']:
                operations.append({
                    'type': 'delete',
                    'bookmark_id': item['id'],
                    'reason': f"删除重复书签: {item['name']}",
                    'details': {
                        'url': item['url'],
                        'path': item['path'],
                        'kept_in': strategy['keep']['path']
                    }
                })

        return operations

    def find_url_issues(self, bookmarks: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        查找 URL 问题(追踪参数、过长URL等)

        Returns:
            问题列表
        """
        issues = []

        def traverse(node, path=""):
            if node.get('type') == 'url':
                url = node.get('url', '')
                name = node.get('name', '')
                bookmark_id = node.get('id', '')

                # 检查追踪参数
                if '?' in url:
                    params = url.split('?', 1)[1]
                    has_tracking = any(
                        f"{param}=" in params
                        for param in self.tracking_params
                    )

                    if has_tracking:
                        issues.append({
                            'type': 'tracking_params',
                            'id': bookmark_id,
                            'name': name,
                            'url': url,
                            'path': path,
                            'severity': 'warning'
                        })

                # 检查过长URL
                if len(url) > 200:
                    issues.append({
                        'type': 'long_url',
                        'id': bookmark_id,
                        'name': name,
                        'url': url,
                        'path': path,
                        'severity': 'info'
                    })

            elif node.get('type') == 'folder':
                folder_name = node.get('name', '')
                new_path = f"{path} > {folder_name}" if path else folder_name

                for child in node.get('children', []):
                    traverse(child, new_path)

        roots = bookmarks.get('roots', {})
        for root_name in ['bookmark_bar', 'other', 'synced']:
            if root_name in roots:
                traverse(roots[root_name], root_name)

        return issues

    def generate_url_clean_operations(self, url_issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        生成 URL 清理操作

        Returns:
            操作列表
        """
        operations = []

        for issue in url_issues:
            if issue['type'] == 'tracking_params':
                operations.append({
                    'type': 'clean_url',
                    'bookmark_id': issue['id'],
                    'reason': f"清理追踪参数: {issue['name']}",
                    'details': {
                        'original_url': issue['url'],
                        'path': issue['path']
                    }
                })

        return operations

    def find_naming_issues(self, bookmarks: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        查找命名问题

        Returns:
            问题列表
        """
        issues = []

        def traverse(node, path=""):
            if node.get('type') == 'url':
                url = node.get('url', '')
                name = node.get('name', '')
                bookmark_id = node.get('id', '')

                # NameYesURL
                if name.startswith('http://') or name.startswith('https://'):
                    issues.append({
                        'type': 'name_is_url',
                        'id': bookmark_id,
                        'name': name,
                        'url': url,
                        'path': path,
                        'severity': 'warning',
                        'suggested_name': self._extract_meaningful_name(url)
                    })

                # NameYes Untitled
                elif name.lower() in ['untitled', 'NoneTitle', '']:
                    issues.append({
                        'type': 'untitled',
                        'id': bookmark_id,
                        'name': name,
                        'url': url,
                        'path': path,
                        'severity': 'warning',
                        'suggested_name': self._extract_meaningful_name(url)
                    })

                # 名称过长
                elif len(name) > 100:
                    issues.append({
                        'type': 'long_name',
                        'id': bookmark_id,
                        'name': name,
                        'url': url,
                        'path': path,
                        'severity': 'info',
                        'suggested_name': name[:80] + '...'
                    })

            elif node.get('type') == 'folder':
                folder_name = node.get('name', '')
                new_path = f"{path} > {folder_name}" if path else folder_name

                for child in node.get('children', []):
                    traverse(child, new_path)

        roots = bookmarks.get('roots', {})
        for root_name in ['bookmark_bar', 'other', 'synced']:
            if root_name in roots:
                traverse(roots[root_name], root_name)

        return issues

    def _extract_meaningful_name(self, url: str) -> str:
        """从 URL 提取有意义的名称"""
        try:
            # 移除协议
            url = re.sub(r'^https?://', '', url)

            # Remove www.
            url = re.sub(r'^www\.', '', url)

            # 提取域名
            domain = url.split('/')[0]

            # 提取路径
            path_parts = url.split('/')[1:] if '/' in url else []

            if path_parts:
                # 使用最后一个有意义的路径部分
                meaningful_part = [p for p in path_parts if p and p not in ['index.html', 'index.php']]
                if meaningful_part:
                    name = meaningful_part[-1]
                    # 移除文件扩展名
                    name = re.sub(r'\.(html|php|aspx)$', '', name)
                    # 替换连字符和下划线为空格
                    name = name.replace('-', ' ').replace('_', ' ')
                    # 首字母大写
                    name = name.title()
                    return f"{name} - {domain}"

            return domain

        except Exception:
            return url[:50]

    def generate_rename_operations(self, naming_issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        生成重命名操作

        Returns:
            操作列表
        """
        operations = []

        for issue in naming_issues:
            if issue.get('suggested_name'):
                operations.append({
                    'type': 'rename',
                    'bookmark_id': issue['id'],
                    'new_name': issue['suggested_name'],
                    'reason': f"优化命名: {issue['type']}",
                    'details': {
                        'original_name': issue['name'],
                        'url': issue['url'],
                        'path': issue['path']
                    }
                })

        return operations

    def generate_smart_fix_plan(self, bookmarks: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成智能修复计划

        Returns:
            修复计划,包含所有操作和统计信息
        """
        # 查找所有问题
        duplicates = self.find_duplicates(bookmarks)
        url_issues = self.find_url_issues(bookmarks)
        naming_issues = self.find_naming_issues(bookmarks)

        # 生成操作
        dedup_ops = self.generate_dedup_operations(duplicates)
        url_clean_ops = self.generate_url_clean_operations(url_issues)
        rename_ops = self.generate_rename_operations(naming_issues)

        all_operations = dedup_ops + url_clean_ops + rename_ops

        return {
            'summary': {
                'total_issues': len(duplicates) + len(url_issues) + len(naming_issues),
                'duplicate_groups': len(duplicates),
                'duplicate_bookmarks': sum(dup['count'] - 1 for dup in duplicates),
                'url_issues': len(url_issues),
                'naming_issues': len(naming_issues),
                'total_operations': len(all_operations)
            },
            'issues': {
                'duplicates': duplicates,
                'url_issues': url_issues,
                'naming_issues': naming_issues
            },
            'operations': all_operations,
            'estimated_time': f"{len(all_operations) * 0.1:.1f} 秒"
        }
