"""
# [CN] 书签修改器
# [CN] 负责安全地修改浏览器书签文件
"""

import json
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import sqlite3


class BackupManager:
    # [CN] """书签备份管理器"""

    def __init__(self, backup_dir: str = "~/.aigard/bookmark_backups"):
        self.backup_dir = Path(backup_dir).expanduser()
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.backup_dir / "backup_index.db"
        self._init_db()

    def _init_db(self):
        # [CN] """初始化备份索引数据库"""
        conn = sqlite3.connect(self.db_path)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS backups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                browser TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                file_path TEXT NOT NULL,
                description TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()

    def create_backup(self, browser: str, source_path: Path, description: str = "") -> str:
        """
        CreateBackup

        Returns:
            backup_id: BackupID
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"{browser}_{timestamp}.json"
        backup_path = self.backup_dir / backup_filename

        # CopyFile
        shutil.copy2(source_path, backup_path)

        # [CN] 记录到数据库
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute('''
            INSERT INTO backups (browser, timestamp, file_path, description)
            VALUES (?, ?, ?, ?)
        ''', (browser, timestamp, str(backup_path), description))
        backup_id = str(cursor.lastrowid)
        conn.commit()
        conn.close()

        return backup_id

    def restore_backup(self, backup_id: str, target_path: Path) -> bool:
        """RestoreBackup"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.execute(
                'SELECT file_path FROM backups WHERE id = ?',
                (backup_id,)
            )
            row = cursor.fetchone()
            conn.close()

            if not row:
                return False

            backup_path = Path(row[0])
            if not backup_path.exists():
                return False

            shutil.copy2(backup_path, target_path)
            return True
        except Exception as e:
            print(f"RestoreBackupFailure: {e}")
            return False

    def list_backups(self, browser: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        # [CN] """列出备份"""
        conn = sqlite3.connect(self.db_path)

        if browser:
            cursor = conn.execute('''
                SELECT id, browser, timestamp, description, created_at
                FROM backups
                WHERE browser = ?
                ORDER BY created_at DESC
                LIMIT ?
            ''', (browser, limit))
        else:
            cursor = conn.execute('''
                SELECT id, browser, timestamp, description, created_at
                FROM backups
                ORDER BY created_at DESC
                LIMIT ?
            ''', (limit,))

        backups = []
        for row in cursor.fetchall():
            backups.append({
                'id': row[0],
                'browser': row[1],
                'timestamp': row[2],
                'description': row[3],
                'created_at': row[4]
            })

        conn.close()
        return backups


class OperationLog:
    # [CN] """操作日志记录器"""

    def __init__(self, log_dir: str = "~/.aigard/bookmark_logs"):
        self.log_dir = Path(log_dir).expanduser()
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.log_dir / "operations.db"
        self._init_db()

    def _init_db(self):
        # [CN] """初始化操作日志数据库"""
        conn = sqlite3.connect(self.db_path)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS operations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                browser TEXT NOT NULL,
                operation_type TEXT NOT NULL,
                details TEXT,
                backup_id TEXT,
                success BOOLEAN,
                error_message TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()

    def add(self, browser: str, operation_type: str, details: Dict[str, Any],
            backup_id: str, success: bool, error_message: str = ""):
        # [CN] """添加操作记录"""
        conn = sqlite3.connect(self.db_path)
        conn.execute('''
            INSERT INTO operations
            (browser, operation_type, details, backup_id, success, error_message)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            browser,
            operation_type,
            json.dumps(details, ensure_ascii=False),
            backup_id,
            success,
            error_message
        ))
        conn.commit()
        conn.close()

    def get_history(self, browser: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        # [CN] """获取操作历史"""
        conn = sqlite3.connect(self.db_path)

        if browser:
            cursor = conn.execute('''
                SELECT id, browser, operation_type, details, backup_id,
                       success, error_message, created_at
                FROM operations
                WHERE browser = ?
                ORDER BY created_at DESC
                LIMIT ?
            ''', (browser, limit))
        else:
            cursor = conn.execute('''
                SELECT id, browser, operation_type, details, backup_id,
                       success, error_message, created_at
                FROM operations
                ORDER BY created_at DESC
                LIMIT ?
            ''', (limit,))

        history = []
        for row in cursor.fetchall():
            history.append({
                'id': row[0],
                'browser': row[1],
                'operation_type': row[2],
                'details': json.loads(row[3]) if row[3] else {},
                'backup_id': row[4],
                'success': bool(row[5]),
                'error_message': row[6],
                'created_at': row[7]
            })

        conn.close()
        return history


class BookmarkModifier:
    # [CN] """书签修改器"""

    BROWSER_PATHS = {
        "chrome": "~/Library/Application Support/Google/Chrome/Default/Bookmarks",
        "edge": "~/Library/Application Support/Microsoft Edge/Default/Bookmarks",
        "dia": "~/Library/Application Support/Dia/User Data/Default/Bookmarks",
        "quark": "~/Library/Application Support/Quark/Default/Bookmarks",
    }

    def __init__(self):
        self.backup_manager = BackupManager()
        self.operation_log = OperationLog()

    def modify(self, browser: str, operations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        执行书签修改操作

        Args:
            browser: 浏览器名称
            operations: 操作列表，每个操作包含 type 和相关参数

        Returns:
            结果字典
        """
        if browser not in self.BROWSER_PATHS:
            return {
                'success': False,
                # [CN] 'error': f'不支持的浏览器: {browser}'
            }

        path = Path(self.BROWSER_PATHS[browser]).expanduser()

        if not path.exists():
            return {
                'success': False,
                # [CN] 'error': f'书签文件不存在: {path}'
            }

        # 1. CreateBackup
        backup_id = self.backup_manager.create_backup(
            browser,
            path,
            # [CN] f"修改前备份 - {len(operations)} 个操作"
        )

        try:
            # [CN] # 2. 加载书签
            with open(path, 'r', encoding='utf-8') as f:
                bookmarks = json.load(f)

            # [CN] # 3. 执行操作
            results = []
            for op in operations:
                result = self._execute_operation(bookmarks, op)
                results.append(result)

            # [CN] # 4. 保存书签
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(bookmarks, f, ensure_ascii=False, indent=2)

            # 5. ValidateModify
            if not self._verify_bookmarks(path):
                # [CN] raise Exception("书签文件验证失败")

            # [CN] # 6. 记录操作
            self.operation_log.add(
                browser,
                'batch_modify',
                {'operations': operations, 'results': results},
                backup_id,
                True
            )

            return {
                'success': True,
                'backup_id': backup_id,
                'operations_count': len(operations),
                'results': results
            }

        except Exception as e:
            # [CN] # 回滚到备份
            self.backup_manager.restore_backup(backup_id, path)

            # RecordFailure
            self.operation_log.add(
                browser,
                'batch_modify',
                {'operations': operations},
                backup_id,
                False,
                str(e)
            )

            return {
                'success': False,
                'error': str(e),
                'backup_id': backup_id
            }

    def _execute_operation(self, bookmarks: Dict[str, Any], operation: Dict[str, Any]) -> Dict[str, Any]:
        # [CN] """执行单个操作"""
        op_type = operation.get('type')

        if op_type == 'delete':
            return self._delete_bookmark(bookmarks, operation)
        elif op_type == 'move':
            return self._move_bookmark(bookmarks, operation)
        elif op_type == 'rename':
            return self._rename_bookmark(bookmarks, operation)
        elif op_type == 'create_folder':
            return self._create_folder(bookmarks, operation)
        elif op_type == 'clean_url':
            return self._clean_url(bookmarks, operation)
        else:
            return {'success': False, 'error': f'未知操作类型: {op_type}'}

    def _delete_bookmark(self, bookmarks: Dict[str, Any], operation: Dict[str, Any]) -> Dict[str, Any]:
        # [CN] """删除书签"""
        bookmark_id = operation.get('bookmark_id')

        def delete_recursive(node):
            if node.get('type') == 'folder':
                children = node.get('children', [])
                node['children'] = [
                    child for child in children
                    if child.get('id') != bookmark_id and delete_recursive(child) is not False
                ]
            elif node.get('id') == bookmark_id:
                return False
            return True

        roots = bookmarks.get('roots', {})
        for root_name in ['bookmark_bar', 'other', 'synced']:
            if root_name in roots:
                delete_recursive(roots[root_name])

        return {'success': True, 'operation': 'delete', 'bookmark_id': bookmark_id}

    def _rename_bookmark(self, bookmarks: Dict[str, Any], operation: Dict[str, Any]) -> Dict[str, Any]:
        # [CN] """重命名书签"""
        bookmark_id = operation.get('bookmark_id')
        new_name = operation.get('new_name')

        def rename_recursive(node):
            if node.get('id') == bookmark_id:
                node['name'] = new_name
                return True
            if node.get('type') == 'folder':
                for child in node.get('children', []):
                    if rename_recursive(child):
                        return True
            return False

        roots = bookmarks.get('roots', {})
        for root_name in ['bookmark_bar', 'other', 'synced']:
            if root_name in roots:
                if rename_recursive(roots[root_name]):
                    break

        return {'success': True, 'operation': 'rename', 'bookmark_id': bookmark_id, 'new_name': new_name}

    def _clean_url(self, bookmarks: Dict[str, Any], operation: Dict[str, Any]) -> Dict[str, Any]:
        # [CN] """清理 URL 追踪参数"""
        bookmark_id = operation.get('bookmark_id')

        # [CN] # 常见追踪参数
        tracking_params = [
            'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
            'fbclid', 'gclid', 'msclkid',
            'ref', 'source', 'from',
            'spm_id_from', 'share_from',
            'sid', 'sessionid'
        ]

        def clean_recursive(node):
            if node.get('id') == bookmark_id and node.get('type') == 'url':
                url = node.get('url', '')
                if '?' in url:
                    base_url, params = url.split('?', 1)
                    param_pairs = params.split('&')
                    cleaned_params = [
                        p for p in param_pairs
                        if not any(p.startswith(f"{tp}=") for tp in tracking_params)
                    ]
                    node['url'] = base_url + ('?' + '&'.join(cleaned_params) if cleaned_params else '')
                return True
            if node.get('type') == 'folder':
                for child in node.get('children', []):
                    if clean_recursive(child):
                        return True
            return False

        roots = bookmarks.get('roots', {})
        for root_name in ['bookmark_bar', 'other', 'synced']:
            if root_name in roots:
                if clean_recursive(roots[root_name]):
                    break

        return {'success': True, 'operation': 'clean_url', 'bookmark_id': bookmark_id}

    def _create_folder(self, bookmarks: Dict[str, Any], operation: Dict[str, Any]) -> Dict[str, Any]:
        # [CN] """创建文件夹"""
        folder_name = operation.get('folder_name')
        parent_id = operation.get('parent_id', 'bookmark_bar')

        import time
        new_folder = {
            'type': 'folder',
            'name': folder_name,
            'children': [],
            'date_added': str(int(time.time() * 1000000)),
            'date_last_used': '0',
            'date_modified': str(int(time.time() * 1000000)),
            'guid': '',
            'id': str(int(time.time() * 1000))
        }

        def add_to_parent(node):
            if node.get('id') == parent_id or (parent_id == 'bookmark_bar' and node.get('type') == 'folder'):
                node.get('children', []).append(new_folder)
                return True
            if node.get('type') == 'folder':
                for child in node.get('children', []):
                    if add_to_parent(child):
                        return True
            return False

        roots = bookmarks.get('roots', {})
        if parent_id in roots:
            roots[parent_id].get('children', []).append(new_folder)
        else:
            for root_name in ['bookmark_bar', 'other', 'synced']:
                if root_name in roots:
                    if add_to_parent(roots[root_name]):
                        break

        return {'success': True, 'operation': 'create_folder', 'folder_name': folder_name}

    def _move_bookmark(self, bookmarks: Dict[str, Any], operation: Dict[str, Any]) -> Dict[str, Any]:
        # [CN] """移动书签"""
        bookmark_id = operation.get('bookmark_id')
        target_folder_id = operation.get('target_folder_id')

        # [CN] # 先找到并移除书签
        bookmark_node = None

        def find_and_remove(node):
            nonlocal bookmark_node
            if node.get('type') == 'folder':
                children = node.get('children', [])
                for i, child in enumerate(children):
                    if child.get('id') == bookmark_id:
                        bookmark_node = children.pop(i)
                        return True
                    if find_and_remove(child):
                        return True
            return False

        # [CN] # 然后添加到目标文件夹
        def add_to_target(node):
            if node.get('id') == target_folder_id:
                node.get('children', []).append(bookmark_node)
                return True
            if node.get('type') == 'folder':
                for child in node.get('children', []):
                    if add_to_target(child):
                        return True
            return False

        roots = bookmarks.get('roots', {})
        for root_name in ['bookmark_bar', 'other', 'synced']:
            if root_name in roots:
                find_and_remove(roots[root_name])

        if bookmark_node:
            for root_name in ['bookmark_bar', 'other', 'synced']:
                if root_name in roots:
                    if add_to_target(roots[root_name]):
                        break

        return {'success': True, 'operation': 'move', 'bookmark_id': bookmark_id}

    def _verify_bookmarks(self, path: Path) -> bool:
        # [CN] """验证书签文件格式正确"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # [CN] 基本结构验证
            if 'roots' not in data:
                return False

            return True
        except Exception:
            return False
