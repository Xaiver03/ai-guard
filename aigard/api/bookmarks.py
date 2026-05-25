"""
书签管理 API 路由
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from aigard.bookmarks import BookmarkManager, BookmarkAnalyzer, get_ai_config

router = APIRouter(prefix="/api/bookmarks", tags=["bookmarks"])

# 全局实例
bookmark_manager = BookmarkManager()
bookmark_analyzer = BookmarkAnalyzer()


# ── 请求/响应模型 ──────────────────────────────────────────────
class AnalyzeRequest(BaseModel):
    browser: str


class CategorizeRequest(BaseModel):
    browser: str
    max_bookmarks: int = 50


class SearchRequest(BaseModel):
    browser: str
    query: str


class ExportRequest(BaseModel):
    browser: str
    format: str = "json"  # json, html, csv


class SuggestNameRequest(BaseModel):
    url: str
    current_name: str = ""


class CleanUrlRequest(BaseModel):
    url: str


# ── 浏览器检测 ────────────────────────────────────────────────
@router.get("/browsers")
def get_browsers():
    """获取检测到的浏览器列表"""
    browsers = bookmark_manager.get_detected_browsers()
    return {
        "browsers": browsers,
        "count": len(browsers)
    }


# ── 书签读取 ──────────────────────────────────────────────────
@router.get("/{browser}")
def get_bookmarks(browser: str):
    """获取指定浏览器的所有书签"""
    if browser not in bookmark_manager.detected_browsers:
        raise HTTPException(status_code=404, detail=f"浏览器 {browser} 未检测到")

    bookmarks = bookmark_manager.extract_all_bookmarks(browser)

    # Safari 权限问题特殊处理
    if bookmarks is None and browser == "safari":
        raise HTTPException(
            status_code=403,
            detail="Safari 书签需要「完全磁盘访问权限」。请前往：系统设置 → 隐私与安全性 → 完全磁盘访问权限，勾选 AI Guard。"
        )

    if bookmarks is None:
        raise HTTPException(status_code=500, detail=f"读取 {browser} 书签失败")

    return {
        "browser": browser,
        "bookmarks": bookmarks,
        "count": len(bookmarks)
    }


# ── 书签统计 ──────────────────────────────────────────────────
@router.get("/{browser}/stats")
def get_bookmark_stats(browser: str):
    """获取书签统计信息"""
    if browser not in bookmark_manager.detected_browsers:
        raise HTTPException(status_code=404, detail=f"浏览器 {browser} 未检测到")

    stats = bookmark_manager.get_bookmark_stats(browser)
    return {
        "browser": browser,
        "stats": stats
    }


# ── 书签分析 ──────────────────────────────────────────────────
@router.post("/analyze")
def analyze_bookmarks(req: AnalyzeRequest):
    """分析书签，识别问题"""
    if req.browser not in bookmark_manager.detected_browsers:
        raise HTTPException(status_code=404, detail=f"浏览器 {req.browser} 未检测到")

    bookmarks = bookmark_manager.extract_all_bookmarks(req.browser)
    if not bookmarks:
        raise HTTPException(status_code=500, detail=f"读取 {req.browser} 书签失败")

    analysis = bookmark_analyzer.analyze_bookmarks(bookmarks)
    return {
        "browser": req.browser,
        "analysis": analysis
    }


# ── AI 分类建议 ───────────────────────────────────────────────
@router.post("/categorize")
async def categorize_bookmarks(req: CategorizeRequest):
    """使用 AI 对书签进行分类建议"""
    if req.browser not in bookmark_manager.detected_browsers:
        raise HTTPException(status_code=404, detail=f"浏览器 {req.browser} 未检测到")

    bookmarks = bookmark_manager.extract_all_bookmarks(req.browser)
    if not bookmarks:
        raise HTTPException(status_code=500, detail=f"读取 {req.browser} 书签失败")

    result = await bookmark_analyzer.ai_categorize_bookmarks(bookmarks, req.max_bookmarks)

    if "error" in result:
        raise HTTPException(status_code=500, detail=result.get("message", "AI 分类失败"))

    return {
        "browser": req.browser,
        "result": result
    }


# ── 书签搜索 ──────────────────────────────────────────────────
@router.post("/search")
def search_bookmarks(req: SearchRequest):
    """搜索书签"""
    if req.browser not in bookmark_manager.detected_browsers:
        raise HTTPException(status_code=404, detail=f"浏览器 {req.browser} 未检测到")

    results = bookmark_manager.search_bookmarks(req.browser, req.query)
    return {
        "browser": req.browser,
        "query": req.query,
        "results": results,
        "count": len(results)
    }


# ── 书签导出 ──────────────────────────────────────────────────
@router.post("/export")
def export_bookmarks(req: ExportRequest):
    """导出书签"""
    if req.browser not in bookmark_manager.detected_browsers:
        raise HTTPException(status_code=404, detail=f"浏览器 {req.browser} 未检测到")

    if req.format not in ["json", "html", "csv"]:
        raise HTTPException(status_code=400, detail="不支持的导出格式")

    # 导出到临时文件
    import tempfile
    from pathlib import Path

    temp_dir = Path(tempfile.gettempdir())
    output_path = temp_dir / f"{req.browser}_bookmarks.{req.format}"

    try:
        bookmark_manager.export_bookmarks(req.browser, str(output_path), req.format)
        return {
            "browser": req.browser,
            "format": req.format,
            "path": str(output_path),
            "message": f"书签已导出到 {output_path}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail="导出失败")


# ── AI 工具 ───────────────────────────────────────────────────
@router.post("/ai/suggest-name")
async def suggest_bookmark_name(req: SuggestNameRequest):
    """使用 AI 建议书签名称"""
    suggested_name = await bookmark_analyzer.ai_suggest_bookmark_name(req.url, req.current_name)
    return {
        "url": req.url,
        "current_name": req.current_name,
        "suggested_name": suggested_name
    }


@router.post("/ai/clean-url")
def clean_bookmark_url(req: CleanUrlRequest):
    """清理 URL（移除追踪参数）"""
    cleaned_url = bookmark_analyzer.clean_url(req.url)
    return {
        "original_url": req.url,
        "cleaned_url": cleaned_url,
        "changed": req.url != cleaned_url
    }


# ── AI 配置 ───────────────────────────────────────────────────
@router.get("/ai/config")
def get_ai_config_status():
    """获取 AI 配置状态"""
    config = get_ai_config()
    return config.to_dict()


@router.post("/ai/config/reload")
def reload_ai_config_endpoint():
    """重新加载 AI 配置"""
    from aigard.bookmarks import reload_ai_config
    config = reload_ai_config()
    return {
        "message": "AI 配置已重新加载",
        "config": config.to_dict()
    }
