"""
书签存储层
封装 CRUD 操作,提供高层接口
"""

from typing import Optional, List, Dict, Any
from .models import BookmarkDatabase, Bookmark, Folder, Tag


class BookmarkStore:
    """书签存储管理器 - 统一入口"""

    def __init__(self, db_path: Optional[str] = None):
        self.db = BookmarkDatabase(db_path)
        self.bookmark = Bookmark(self.db)
        self.folder = Folder(self.db)
        self.tag = Tag(self.db)

    # ── 文件夹操作 ────────────────────────────────────────────────────

    def create_folder(self, name: str, parent_id: Optional[int] = None) -> dict:
        folder_id = self.folder.create(name, parent_id)
        return self.folder.get(folder_id)

    def get_folder_tree(self) -> List[dict]:
        """获取文件夹树形结构"""
        all_folders = self.folder.list_all()

        # 统计每个文件夹的书签数
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT folder_id, COUNT(*) as count FROM bookmarks GROUP BY folder_id")
        counts = {row['folder_id']: row['count'] for row in cursor.fetchall()}
        conn.close()

        # 构建树形结构
        folder_map = {}
        for f in all_folders:
            f['children'] = []
            f['bookmark_count'] = counts.get(f['id'], 0)
            folder_map[f['id']] = f

        roots = []
        for f in all_folders:
            parent_id = f.get('parent_id')
            if parent_id and parent_id in folder_map:
                folder_map[parent_id]['children'].append(f)
            else:
                roots.append(f)

        return roots

    def update_folder(self, folder_id: int, name: Optional[str] = None,
                      parent_id: Optional[int] = None) -> Optional[dict]:
        self.folder.update(folder_id, name=name, parent_id=parent_id)
        return self.folder.get(folder_id)

    def delete_folder(self, folder_id: int):
        self.folder.delete(folder_id)

    # ── 标签操作 ──────────────────────────────────────────────────────

    def create_tag(self, name: str, color: str = "#58a6ff") -> dict:
        tag_id = self.tag.create(name, color)
        return self.tag.get(tag_id)

    def list_tags(self) -> List[dict]:
        tags = self.tag.list_all()
        # 统计每个标签的书签数
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT tag_id, COUNT(*) as count FROM bookmark_tags GROUP BY tag_id")
        counts = {row['tag_id']: row['count'] for row in cursor.fetchall()}
        conn.close()

        for t in tags:
            t['bookmark_count'] = counts.get(t['id'], 0)

        return tags

    def update_tag(self, tag_id: int, name: Optional[str] = None,
                   color: Optional[str] = None) -> Optional[dict]:
        self.tag.update(tag_id, name=name, color=color)
        return self.tag.get(tag_id)

    def delete_tag(self, tag_id: int):
        self.tag.delete(tag_id)

    # ── 书签操作 ──────────────────────────────────────────────────────

    def create_bookmark(self, name: str, url: str, folder_id: Optional[int] = None,
                        description: str = "", icon: str = "",
                        tag_names: Optional[List[str]] = None) -> dict:
        bookmark_id = self.bookmark.create(name, url, folder_id, description, icon)

        # 添加标签
        if tag_names:
            for tag_name in tag_names:
                tag_id = self.tag.create(tag_name)
                self.bookmark.add_tag(bookmark_id, tag_id)

        return self.bookmark.get(bookmark_id)

    def get_bookmark(self, bookmark_id: int) -> Optional[dict]:
        return self.bookmark.get(bookmark_id)

    def list_bookmarks(self, folder_id: Optional[int] = None,
                       tag_id: Optional[int] = None) -> List[dict]:
        return self.bookmark.list_all(folder_id=folder_id, tag_id=tag_id)

    def search_bookmarks(self, query: str) -> List[dict]:
        return self.bookmark.search(query)

    def update_bookmark(self, bookmark_id: int, **kwargs) -> Optional[dict]:
        # 处理标签更新
        tag_names = kwargs.pop('tag_names', None)

        self.bookmark.update(bookmark_id, **kwargs)

        if tag_names is not None:
            # 替换所有标签
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM bookmark_tags WHERE bookmark_id = ?", (bookmark_id,))
            conn.commit()
            conn.close()

            for tag_name in tag_names:
                tag_id = self.tag.create(tag_name)
                self.bookmark.add_tag(bookmark_id, tag_id)

        return self.bookmark.get(bookmark_id)

    def delete_bookmark(self, bookmark_id: int):
        self.bookmark.delete(bookmark_id)

    def move_bookmark(self, bookmark_id: int, folder_id: Optional[int]) -> Optional[dict]:
        self.bookmark.update(bookmark_id, folder_id=folder_id)
        return self.bookmark.get(bookmark_id)

    def add_tag_to_bookmark(self, bookmark_id: int, tag_id: int):
        self.bookmark.add_tag(bookmark_id, tag_id)

    def remove_tag_from_bookmark(self, bookmark_id: int, tag_id: int):
        self.bookmark.remove_tag(bookmark_id, tag_id)

    # ── 统计 ──────────────────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) as count FROM bookmarks")
        total_bookmarks = cursor.fetchone()['count']

        cursor.execute("SELECT COUNT(*) as count FROM folders")
        total_folders = cursor.fetchone()['count']

        cursor.execute("SELECT COUNT(*) as count FROM tags")
        total_tags = cursor.fetchone()['count']

        cursor.execute("SELECT COUNT(*) as count FROM bookmarks WHERE check_status = 'dead'")
        dead_links = cursor.fetchone()['count']

        cursor.execute("SELECT COUNT(*) as count FROM bookmarks WHERE check_status = 'unknown'")
        unchecked = cursor.fetchone()['count']

        conn.close()

        return {
            "total_bookmarks": total_bookmarks,
            "total_folders": total_folders,
            "total_tags": total_tags,
            "dead_links": dead_links,
            "unchecked": unchecked,
        }

    # ── 批量导入 ──────────────────────────────────────────────────────

    def import_bookmarks(self, bookmarks: List[Dict[str, Any]],
                         source_browser: str = "") -> Dict[str, int]:
        """
        批量导入书签(从浏览器导入)
        bookmarks: [{"name": ..., "url": ..., "folder": "path/to/folder"}]
        返回: {"imported": N, "skipped": N, "folders_created": N}
        """
        imported = 0
        skipped = 0
        folders_created = 0

        # 缓存文件夹路径 → ID 的映射
        folder_cache: Dict[str, int] = {}

        # 获取已有 URL 集合(去重)
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT url FROM bookmarks")
        existing_urls = {row['url'] for row in cursor.fetchall()}
        conn.close()

        for bm in bookmarks:
            url = bm.get('url', '').strip()
            name = bm.get('name', '').strip() or url
            folder_path = bm.get('folder', '').strip()

            if not url:
                skipped += 1
                continue

            # 跳过重复 URL
            if url in existing_urls:
                skipped += 1
                continue

            # 解析/创建文件夹路径
            folder_id = None
            if folder_path:
                if folder_path not in folder_cache:
                    folder_id, created = self._ensure_folder_path(folder_path)
                    folders_created += created
                    folder_cache[folder_path] = folder_id
                else:
                    folder_id = folder_cache[folder_path]

            self.bookmark.create(name, url, folder_id)
            existing_urls.add(url)
            imported += 1

        return {
            "imported": imported,
            "skipped": skipped,
            "folders_created": folders_created,
        }

    def _ensure_folder_path(self, path: str) -> tuple:
        """
        确保文件夹路径存在,不存在则创建
        path: "父文件夹/子文件夹"
        返回: (folder_id, created_count)
        """
        parts = [p.strip() for p in path.split('/') if p.strip()]
        created = 0
        parent_id = None

        conn = self.db.get_connection()
        cursor = conn.cursor()

        for part in parts:
            if parent_id is None:
                cursor.execute(
                    "SELECT id FROM folders WHERE name = ? AND parent_id IS NULL", (part,)
                )
            else:
                cursor.execute(
                    "SELECT id FROM folders WHERE name = ? AND parent_id = ?", (part, parent_id)
                )

            row = cursor.fetchone()
            if row:
                parent_id = row['id']
            else:
                conn.close()
                parent_id = self.folder.create(part, parent_id)
                created += 1
                conn = self.db.get_connection()
                cursor = conn.cursor()

        conn.close()
        return parent_id, created
