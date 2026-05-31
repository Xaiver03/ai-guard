"""
书签数据模型
参考 OneNav 的数据库设计,使用 SQLite 存储
"""

from datetime import datetime
from typing import Optional, List
from pathlib import Path
from dataclasses import dataclass, field
import sqlite3
import json


@dataclass
class BookmarkData:
    """书签数据类（用于 AI 分析）"""
    id: int
    name: str
    url: str
    folder_id: Optional[int] = None
    description: str = ""
    icon: str = ""
    order_index: int = 0
    tags: List[dict] = field(default_factory=list)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    last_checked: Optional[str] = None
    status: str = "active"


@dataclass
class Category:
    """书签分类（文件夹）"""
    id: int
    name: str
    parent_id: Optional[int] = None
    order_index: int = 0


class BookmarkDatabase:
    """书签数据库管理"""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = str(Path.home() / ".aigard" / "bookmarks.db")

        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    def _init_database(self):
        """初始化数据库表结构"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 文件夹表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS folders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                parent_id INTEGER,
                order_index INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (parent_id) REFERENCES folders(id) ON DELETE CASCADE
            )
        """)

        # 标签表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                color TEXT DEFAULT '#58a6ff',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 书签表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bookmarks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                url TEXT NOT NULL,
                folder_id INTEGER,
                description TEXT,
                icon TEXT,
                order_index INTEGER DEFAULT 0,
                last_check_at TIMESTAMP,
                check_status TEXT DEFAULT 'unknown',
                check_status_code INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (folder_id) REFERENCES folders(id) ON DELETE SET NULL
            )
        """)

        # 书签-标签关联表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bookmark_tags (
                bookmark_id INTEGER NOT NULL,
                tag_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (bookmark_id, tag_id),
                FOREIGN KEY (bookmark_id) REFERENCES bookmarks(id) ON DELETE CASCADE,
                FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
            )
        """)

        # 创建索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_bookmarks_folder ON bookmarks(folder_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_bookmarks_url ON bookmarks(url)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_folders_parent ON folders(parent_id)")

        conn.commit()
        conn.close()

    def get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn


class Folder:
    """文件夹模型"""

    def __init__(self, db: BookmarkDatabase):
        self.db = db

    def create(self, name: str, parent_id: Optional[int] = None, order_index: int = 0) -> int:
        """创建文件夹"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO folders (name, parent_id, order_index)
            VALUES (?, ?, ?)
        """, (name, parent_id, order_index))

        folder_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return folder_id

    def get(self, folder_id: int) -> Optional[dict]:
        """获取文件夹"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM folders WHERE id = ?", (folder_id,))
        row = cursor.fetchone()
        conn.close()

        return dict(row) if row else None

    def list_all(self) -> List[dict]:
        """获取所有文件夹"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM folders ORDER BY parent_id, order_index, name")
        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def update(self, folder_id: int, name: str | None = None,
               parent_id: int | None = None, order_index: int | None = None):
        """更新文件夹"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        updates: list[str] = []
        params: list[str | int] = []

        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if parent_id is not None:
            updates.append("parent_id = ?")
            params.append(parent_id)
        if order_index is not None:
            updates.append("order_index = ?")
            params.append(order_index)

        if updates:
            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(folder_id)

            cursor.execute(f"""
                UPDATE folders SET {', '.join(updates)}
                WHERE id = ?
            """, params)

            conn.commit()

        conn.close()

    def delete(self, folder_id: int):
        """删除文件夹(级联删除子文件夹,书签移到根目录)"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        # 将该文件夹下的书签移到根目录
        cursor.execute("UPDATE bookmarks SET folder_id = NULL WHERE folder_id = ?", (folder_id,))

        # 删除文件夹(子文件夹会被级联删除)
        cursor.execute("DELETE FROM folders WHERE id = ?", (folder_id,))

        conn.commit()
        conn.close()


class Tag:
    """标签模型"""

    def __init__(self, db: BookmarkDatabase):
        self.db = db

    def create(self, name: str, color: str = "#58a6ff") -> int:
        """创建标签"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("INSERT INTO tags (name, color) VALUES (?, ?)", (name, color))
            tag_id = cursor.lastrowid
            conn.commit()
            return tag_id if tag_id else 0
        except sqlite3.IntegrityError:
            # 标签已存在,返回现有 ID
            cursor.execute("SELECT id FROM tags WHERE name = ?", (name,))
            row = cursor.fetchone()
            return row[0] if row else 0
        finally:
            conn.close()

    def get(self, tag_id: int) -> Optional[dict]:
        """获取标签"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM tags WHERE id = ?", (tag_id,))
        row = cursor.fetchone()
        conn.close()

        return dict(row) if row else None

    def list_all(self) -> List[dict]:
        """获取所有标签"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM tags ORDER BY name")
        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def update(self, tag_id: int, name: Optional[str] = None, color: Optional[str] = None):
        """更新标签"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        updates: list[str] = []
        params: list[str | int] = []

        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if color is not None:
            updates.append("color = ?")
            params.append(color)

        if updates:
            params.append(tag_id)
            cursor.execute(f"UPDATE tags SET {', '.join(updates)} WHERE id = ?", params)
            conn.commit()

        conn.close()

    def delete(self, tag_id: int):
        """删除标签(级联删除关联关系)"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM tags WHERE id = ?", (tag_id,))
        conn.commit()
        conn.close()


class Bookmark:
    """书签模型"""

    def __init__(self, db: BookmarkDatabase):
        self.db = db

    def create(self, name: str, url: str, folder_id: Optional[int] = None,
               description: str = "", icon: str = "", order_index: int = 0) -> int:
        """创建书签"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO bookmarks (name, url, folder_id, description, icon, order_index)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (name, url, folder_id, description, icon, order_index))

        bookmark_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return bookmark_id

    def get(self, bookmark_id: int) -> Optional[dict]:
        """获取书签(包含标签)"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM bookmarks WHERE id = ?", (bookmark_id,))
        row = cursor.fetchone()

        if not row:
            conn.close()
            return None

        bookmark = dict(row)

        # 获取标签
        cursor.execute("""
            SELECT t.* FROM tags t
            JOIN bookmark_tags bt ON t.id = bt.tag_id
            WHERE bt.bookmark_id = ?
        """, (bookmark_id,))

        bookmark['tags'] = [dict(tag) for tag in cursor.fetchall()]
        conn.close()

        return bookmark

    def list_all(self, folder_id: Optional[int] = None, tag_id: Optional[int] = None) -> List[dict]:
        """获取书签列表"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        query = "SELECT * FROM bookmarks"
        params = []

        if folder_id is not None:
            query += " WHERE folder_id = ?"
            params.append(folder_id)
        elif tag_id is not None:
            query = """
                SELECT b.* FROM bookmarks b
                JOIN bookmark_tags bt ON b.id = bt.bookmark_id
                WHERE bt.tag_id = ?
            """
            params.append(tag_id)

        query += " ORDER BY order_index, name"

        cursor.execute(query, params)
        rows = cursor.fetchall()

        bookmarks = []
        for row in rows:
            bookmark = dict(row)

            # 获取标签
            cursor.execute("""
                SELECT t.* FROM tags t
                JOIN bookmark_tags bt ON t.id = bt.tag_id
                WHERE bt.bookmark_id = ?
            """, (bookmark['id'],))

            bookmark['tags'] = [dict(tag) for tag in cursor.fetchall()]
            bookmarks.append(bookmark)

        conn.close()
        return bookmarks

    def search(self, query: str) -> List[dict]:
        """搜索书签"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM bookmarks
            WHERE name LIKE ? OR url LIKE ? OR description LIKE ?
            ORDER BY name
        """, (f"%{query}%", f"%{query}%", f"%{query}%"))

        rows = cursor.fetchall()

        bookmarks = []
        for row in rows:
            bookmark = dict(row)

            # 获取标签
            cursor.execute("""
                SELECT t.* FROM tags t
                JOIN bookmark_tags bt ON t.id = bt.tag_id
                WHERE bt.bookmark_id = ?
            """, (bookmark['id'],))

            bookmark['tags'] = [dict(tag) for tag in cursor.fetchall()]
            bookmarks.append(bookmark)

        conn.close()
        return bookmarks

    def update(self, bookmark_id: int, **kwargs):
        """更新书签"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        allowed_fields = ['name', 'url', 'folder_id', 'description', 'icon', 'order_index',
                         'last_check_at', 'check_status', 'check_status_code']

        updates = []
        params = []

        for field in allowed_fields:
            if field in kwargs:
                updates.append(f"{field} = ?")
                params.append(kwargs[field])

        if updates:
            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(bookmark_id)

            cursor.execute(f"""
                UPDATE bookmarks SET {', '.join(updates)}
                WHERE id = ?
            """, params)

            conn.commit()

        conn.close()

    def delete(self, bookmark_id: int):
        """删除书签"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM bookmarks WHERE id = ?", (bookmark_id,))
        conn.commit()
        conn.close()

    def add_tag(self, bookmark_id: int, tag_id: int):
        """为书签添加标签"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO bookmark_tags (bookmark_id, tag_id)
                VALUES (?, ?)
            """, (bookmark_id, tag_id))
            conn.commit()
        except sqlite3.IntegrityError:
            pass  # 已存在
        finally:
            conn.close()

    def remove_tag(self, bookmark_id: int, tag_id: int):
        """移除书签的标签"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM bookmark_tags
            WHERE bookmark_id = ? AND tag_id = ?
        """, (bookmark_id, tag_id))

        conn.commit()
        conn.close()

    def get_tags(self, bookmark_id: int) -> List[dict]:
        """获取书签的所有标签"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT t.* FROM tags t
            JOIN bookmark_tags bt ON t.id = bt.tag_id
            WHERE bt.bookmark_id = ?
        """, (bookmark_id,))

        tags = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return tags
