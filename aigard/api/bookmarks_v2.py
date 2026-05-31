"""
书签管理 API v2 - OneNav 风格
整合新的数据库存储和旧的浏览器导入功能
"""

from typing import cast, List, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from aigard.bookmarks import (
    BookmarkStore, LinkChecker, BookmarkManager,
    BookmarkAnalyzer, get_ai_config
)

router = APIRouter(prefix="/api/bookmarks/v2", tags=["bookmarks-v2"])

# 全局实例
store = BookmarkStore()
link_checker = LinkChecker(store)
browser_manager = BookmarkManager()  # 用于从浏览器导入
analyzer = BookmarkAnalyzer()


# ── Request Models ────────────────────────────────────────────────────

class CreateFolderRequest(BaseModel):
    name: str
    parent_id: Optional[int] = None


class UpdateFolderRequest(BaseModel):
    name: Optional[str] = None
    parent_id: Optional[int] = None


class CreateTagRequest(BaseModel):
    name: str
    color: str = "#58a6ff"


class UpdateTagRequest(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None


class CreateBookmarkRequest(BaseModel):
    name: str
    url: str
    folder_id: Optional[int] = None
    description: str = ""
    icon: str = ""
    tag_names: Optional[List[str]] = None


class UpdateBookmarkRequest(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    folder_id: Optional[int] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    tag_names: Optional[List[str]] = None


class MoveBookmarkRequest(BaseModel):
    folder_id: Optional[int]


class ImportFromBrowserRequest(BaseModel):
    browser: str  # chrome, edge, safari, etc.


class CheckLinksRequest(BaseModel):
    bookmark_ids: Optional[List[int]] = None


class AddTagRequest(BaseModel):
    tag_id: int


# ── 文件夹 API ────────────────────────────────────────────────────────

@router.get("/folders")
def get_folders():
    """获取文件夹树"""
    tree = store.get_folder_tree()
    return {"folders": tree}


@router.post("/folders")
def create_folder(req: CreateFolderRequest):
    """创建文件夹"""
    folder = store.create_folder(req.name, req.parent_id)
    return {"folder": folder}


@router.put("/folders/{folder_id}")
def update_folder(folder_id: int, req: UpdateFolderRequest):
    """更新文件夹"""
    folder = store.update_folder(folder_id, req.name, req.parent_id)
    if not folder:
        raise HTTPException(status_code=404, detail="文件夹不存在")
    return {"folder": folder}


@router.delete("/folders/{folder_id}")
def delete_folder(folder_id: int):
    """删除文件夹"""
    store.delete_folder(folder_id)
    return {"message": "文件夹已删除"}


# ── 标签 API ──────────────────────────────────────────────────────────

@router.get("/tags")
def get_tags():
    """获取所有标签"""
    tags = store.list_tags()
    return {"tags": tags}


@router.post("/tags")
def create_tag(req: CreateTagRequest):
    """创建标签"""
    tag = store.create_tag(req.name, req.color)
    return {"tag": tag}


@router.put("/tags/{tag_id}")
def update_tag(tag_id: int, req: UpdateTagRequest):
    """更新标签"""
    tag = store.update_tag(tag_id, req.name, req.color)
    if not tag:
        raise HTTPException(status_code=404, detail="标签不存在")
    return {"tag": tag}


@router.delete("/tags/{tag_id}")
def delete_tag(tag_id: int):
    """删除标签"""
    store.delete_tag(tag_id)
    return {"message": "标签已删除"}


# ── 书签 API ──────────────────────────────────────────────────────────

@router.get("/bookmarks")
def get_bookmarks(folder_id: Optional[int] = None, tag_id: Optional[int] = None):
    """获取书签列表"""
    bookmarks = store.list_bookmarks(folder_id=folder_id, tag_id=tag_id)
    return {"bookmarks": bookmarks, "count": len(bookmarks)}


@router.get("/bookmarks/{bookmark_id}")
def get_bookmark(bookmark_id: int):
    """获取单个书签"""
    bookmark = store.get_bookmark(bookmark_id)
    if not bookmark:
        raise HTTPException(status_code=404, detail="书签不存在")
    return {"bookmark": bookmark}


@router.post("/bookmarks")
def create_bookmark(req: CreateBookmarkRequest):
    """创建书签"""
    bookmark = store.create_bookmark(
        req.name, req.url, req.folder_id,
        req.description, req.icon, req.tag_names
    )
    return {"bookmark": bookmark}


@router.put("/bookmarks/{bookmark_id}")
def update_bookmark(bookmark_id: int, req: UpdateBookmarkRequest):
    """更新书签"""
    update_data = req.dict(exclude_unset=True)
    bookmark = store.update_bookmark(bookmark_id, **update_data)
    if not bookmark:
        raise HTTPException(status_code=404, detail="书签不存在")
    return {"bookmark": bookmark}


@router.delete("/bookmarks/{bookmark_id}")
def delete_bookmark(bookmark_id: int):
    """删除书签"""
    store.delete_bookmark(bookmark_id)
    return {"message": "书签已删除"}


@router.post("/bookmarks/{bookmark_id}/move")
def move_bookmark(bookmark_id: int, req: MoveBookmarkRequest):
    """移动书签到文件夹"""
    bookmark = store.move_bookmark(bookmark_id, req.folder_id)
    if not bookmark:
        raise HTTPException(status_code=404, detail="书签不存在")
    return {"bookmark": bookmark}


@router.post("/bookmarks/{bookmark_id}/tags")
def add_tag_to_bookmark(bookmark_id: int, req: AddTagRequest):
    """为书签添加标签"""
    store.add_tag_to_bookmark(bookmark_id, req.tag_id)
    bookmark = store.get_bookmark(bookmark_id)
    return {"bookmark": bookmark}


@router.delete("/bookmarks/{bookmark_id}/tags/{tag_id}")
def remove_tag_from_bookmark(bookmark_id: int, tag_id: int):
    """移除书签的标签"""
    store.remove_tag_from_bookmark(bookmark_id, tag_id)
    bookmark = store.get_bookmark(bookmark_id)
    return {"bookmark": bookmark}


# ── 搜索 API ──────────────────────────────────────────────────────────

@router.get("/search")
def search_bookmarks(q: str):
    """搜索书签"""
    bookmarks = store.search_bookmarks(q)
    return {"bookmarks": bookmarks, "count": len(bookmarks)}


# ── 统计 API ──────────────────────────────────────────────────────────

@router.get("/stats")
def get_stats():
    """获取统计信息"""
    stats = store.get_stats()
    return {"stats": stats}


# ── 导入 API ──────────────────────────────────────────────────────────

@router.post("/import/browser")
def import_from_browser(req: ImportFromBrowserRequest):
    """从浏览器导入书签到数据库"""
    if req.browser not in browser_manager.detected_browsers:
        raise HTTPException(status_code=404, detail=f"浏览器 {req.browser} 未检测到")

    # 从浏览器读取书签
    bookmarks = browser_manager.extract_all_bookmarks(req.browser)
    if not bookmarks:
        raise HTTPException(status_code=500, detail=f"读取 {req.browser} 书签失败")

    # 导入到数据库
    result = store.import_bookmarks(bookmarks, req.browser)

    return {
        "browser": req.browser,
        "result": result
    }


@router.get("/import/browsers")
def get_available_browsers():
    """获取可导入的浏览器列表"""
    browsers = browser_manager.get_detected_browsers()
    return {"browsers": browsers}


# ── 链接检测 API ──────────────────────────────────────────────────────

@router.post("/check-links")
async def check_links(req: CheckLinksRequest, background_tasks: BackgroundTasks):
    """批量检测链接"""
    result = await link_checker.check_bookmarks(req.bookmark_ids)
    return {"result": result}


@router.get("/dead-links")
def get_dead_links():
    """获取所有死链"""
    bookmarks = link_checker.get_dead_links()
    return {"bookmarks": bookmarks, "count": len(bookmarks)}


@router.get("/unchecked-links")
def get_unchecked_links():
    """获取未检测的链接"""
    bookmarks = link_checker.get_unchecked_links()
    return {"bookmarks": bookmarks, "count": len(bookmarks)}


# ── AI 功能 API ───────────────────────────────────────────────────────

@router.post("/ai/analyze")
def ai_analyze():
    """AI 分析所有书签"""
    bookmarks = store.list_bookmarks()

    # 转换为旧格式(兼容 BookmarkAnalyzer)
    legacy_bookmarks = [
        {
            "name": bm['name'],
            "url": bm['url'],
            "folder": "",  # 暂时不需要
        }
        for bm in bookmarks
    ]

    analysis = analyzer.analyze_bookmarks(legacy_bookmarks)
    return {"analysis": analysis}


@router.post("/ai/categorize")
async def ai_categorize(max_bookmarks: int = 50):
    """AI 智能分类"""
    bookmarks = store.list_bookmarks()[:max_bookmarks]

    # 转换为旧格式
    legacy_bookmarks = [
        {
            "name": bm['name'],
            "url": bm['url'],
            "folder": "",
        }
        for bm in bookmarks
    ]

    result = await analyzer.ai_categorize_bookmarks(legacy_bookmarks, max_bookmarks)  # type: ignore[arg-type]
    return {"result": result}


@router.get("/ai/config")
def get_ai_config_status():
    """获取 AI 配置状态"""
    config = get_ai_config()
    return config.to_dict()
