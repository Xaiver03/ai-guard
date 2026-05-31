"""
链接检测功能
批量检测书签 URL 可用性
"""

import asyncio
import aiohttp
import ssl
from typing import List, Dict, Optional, Any
from datetime import datetime
from .store import BookmarkStore


class LinkChecker:
    """链接检测器"""

    def __init__(self, store: BookmarkStore, timeout: int = 10, max_concurrent: int = 10):
        self.store = store
        self.timeout = timeout
        self.max_concurrent = max_concurrent

    async def check_url(self, url: str, session: aiohttp.ClientSession) -> Dict[str, Any]:
        """检测单个 URL"""
        try:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            async with session.head(url, timeout=timeout, allow_redirects=True) as response:
                return {
                    "url": url,
                    "status": "alive" if response.status < 400 else "dead",
                    "status_code": response.status,
                    "checked_at": datetime.now().isoformat(),
                }
        except asyncio.TimeoutError:
            return {
                "url": url,
                "status": "timeout",
                "status_code": None,
                "checked_at": datetime.now().isoformat(),
            }
        except Exception as e:
            return {
                "url": url,
                "status": "error",
                "status_code": None,
                "error": str(e),
                "checked_at": datetime.now().isoformat(),
            }

    async def check_bookmarks(self, bookmark_ids: Optional[List[int]] = None) -> Dict[str, Any]:
        """
        批量检测书签
        bookmark_ids: 指定书签 ID 列表,None 表示检测所有
        """
        if bookmark_ids:
            bookmarks_raw = [self.store.get_bookmark(bid) for bid in bookmark_ids]
            bookmarks = [b for b in bookmarks_raw if b]
        else:
            bookmarks = self.store.list_bookmarks()

        if not bookmarks:
            return {"total": 0, "alive": 0, "dead": 0, "timeout": 0, "error": 0}

        results: Dict[str, Any] = {
            "total": len(bookmarks),
            "alive": 0,
            "dead": 0,
            "timeout": 0,
            "error": 0,
            "details": []
        }

        # 创建不验证 SSL 的 context
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        # 创建 aiohttp session
        connector = aiohttp.TCPConnector(limit=self.max_concurrent, ssl=ssl_context)
        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = []
            for bm in bookmarks:
                task = self.check_url(bm['url'], session)
                tasks.append((bm['id'], task))

            # 并发执行
            for bm_id, task in tasks:
                result = await task
                status = result['status']

                # 更新数据库
                self.store.update_bookmark(
                    bm_id,
                    check_status=status,
                    check_status_code=result.get('status_code'),
                    last_check_at=result['checked_at']
                )

                results[status] = results.get(status, 0) + 1
                results['details'].append({
                    "bookmark_id": bm_id,
                    **result
                })

        return results

    def get_dead_links(self) -> List[dict]:
        """获取所有死链"""
        conn = self.store.db.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM bookmarks
            WHERE check_status IN ('dead', 'timeout', 'error')
            ORDER BY last_check_at DESC
        """)

        bookmarks = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return bookmarks

    def get_unchecked_links(self) -> List[dict]:
        """获取未检测的链接"""
        conn = self.store.db.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM bookmarks
            WHERE check_status = 'unknown' OR last_check_at IS NULL
            ORDER BY created_at DESC
        """)

        bookmarks = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return bookmarks
