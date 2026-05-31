"""
# [CN] 书签管理 API 路由
"""

from typing import cast, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from aigard.bookmarks import (
    BookmarkManager, BookmarkAnalyzer, get_ai_config,
    BookmarkModifier, BrowserStateDetector, BookmarkFixer,
    BackupManager, OperationLog
)

router = APIRouter(prefix="/api/bookmarks", tags=["bookmarks"])

# [CN] 全局实例
bookmark_manager = BookmarkManager()
bookmark_analyzer = BookmarkAnalyzer()
bookmark_modifier = BookmarkModifier()
state_detector = BrowserStateDetector()
bookmark_fixer = BookmarkFixer()
backup_manager = BackupManager()
operation_log = OperationLog()


# ── Request/ResponseModel ──────────────────────────────────────────────
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


# [CN] ── 浏览器检测 ────────────────────────────────────────────────
@router.get("/browsers")
def get_browsers():
    # [CN] """获取检测到的浏览器列表"""
    browsers = bookmark_manager.get_detected_browsers()
    return {
        "browsers": browsers,
        "count": len(browsers)
    }


# [CN] # ── 书签读取 ──────────────────────────────────────────────────
@router.get("/{browser}")
def get_bookmarks(browser: str):
    # [CN] """获取指定浏览器的所有书签"""
    if browser not in bookmark_manager.detected_browsers:
        raise HTTPException(status_code=404, detail=f"浏览器 {browser} 未检测到")

    bookmarks = bookmark_manager.extract_all_bookmarks(browser)

    # [CN] Safari 权限问题特殊处理
    if bookmarks is None and browser == "safari":
        raise HTTPException(
            status_code=403,
            detail="Safari 书签需要「完全磁盘访问权限」。请前往:系统设置 → 隐私与安全性 → 完全磁盘访问权限,勾选 AI Guard。"
        )

    if bookmarks is None:
        raise HTTPException(status_code=500, detail=f"读取 {browser} 书签失败")

    return {
        "browser": browser,
        "bookmarks": bookmarks,
        "count": len(bookmarks)
    }


# [CN] ── 书签统计 ──────────────────────────────────────────────────
@router.get("/{browser}/stats")
def get_bookmark_stats(browser: str):
    """获取书签统计信息"""
    if browser not in bookmark_manager.detected_browsers:
        raise HTTPException(status_code=404, detail=f"Browser {browser} not detected")

    stats = bookmark_manager.get_bookmark_stats(browser)
    return {
        "browser": browser,
        "stats": stats
    }


# [CN] # ── 书签分析 ──────────────────────────────────────────────────
@router.post("/analyze")
def analyze_bookmarks(req: AnalyzeRequest):
    # [CN] """分析书签,识别问题"""
    if req.browser not in bookmark_manager.detected_browsers:
        raise HTTPException(status_code=404, detail=f"浏览器 {req.browser} 未检测到")

    bookmarks = bookmark_manager.extract_all_bookmarks(req.browser)
    if not bookmarks:
        raise HTTPException(status_code=500, detail=f"读取 {req.browser} 书签失败")

    analysis = bookmark_analyzer.analyze_bookmarks(bookmarks)  # type: ignore[arg-type]
    return {
        "browser": req.browser,
        "analysis": analysis
    }


# [CN] ── AI 分类建议 ───────────────────────────────────────────────
@router.post("/categorize")
async def categorize_bookmarks(req: CategorizeRequest):
    """使用 AI 对书签进行分类建议"""
    if req.browser not in bookmark_manager.detected_browsers:
        raise HTTPException(status_code=404, detail=f"浏览器 {req.browser} 未检测到")

    bookmarks = bookmark_manager.extract_all_bookmarks(req.browser)
    if not bookmarks:
        raise HTTPException(status_code=500, detail=f"读取 {req.browser} 书签失败")

    result = await bookmark_analyzer.ai_categorize_bookmarks(bookmarks, req.max_bookmarks)  # type: ignore[arg-type]

    if "error" in result:
        raise HTTPException(status_code=500, detail=result.get("message", "AI 分类失败"))

    return {
        "browser": req.browser,
        "result": result
    }


# [CN] # ── 书签搜索 ──────────────────────────────────────────────────
@router.post("/search")
def search_bookmarks(req: SearchRequest):
    # [CN] """搜索书签"""
    if req.browser not in bookmark_manager.detected_browsers:
        raise HTTPException(status_code=404, detail=f"浏览器 {req.browser} 未检测到")

    results = bookmark_manager.search_bookmarks(req.browser, req.query)
    return {
        "browser": req.browser,
        "query": req.query,
        "results": results,
        "count": len(results)
    }


# [CN] ── 书签导出 ──────────────────────────────────────────────────
@router.post("/export")
def export_bookmarks(req: ExportRequest):
    # [CN] """导出书签"""
    if req.browser not in bookmark_manager.detected_browsers:
        raise HTTPException(status_code=404, detail=f"浏览器 {req.browser} 未检测到")

    if req.format not in ["json", "html", "csv"]:
        raise HTTPException(status_code=400, detail="不支持的导出格式")

    # [CN] # 导出到临时文件
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
            # [CN] "message": f"书签已导出到 {output_path}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail="ExportFailure")


# [CN] # ── AI 工具 ───────────────────────────────────────────────────
@router.post("/ai/suggest-name")
async def suggest_bookmark_name(req: SuggestNameRequest):
    # [CN] """使用 AI 建议书签名称"""
    suggested_name = await bookmark_analyzer.ai_suggest_bookmark_name(req.url, req.current_name)
    return {
        "url": req.url,
        "current_name": req.current_name,
        "suggested_name": suggested_name
    }


@router.post("/ai/clean-url")
def clean_bookmark_url(req: CleanUrlRequest):
    # [CN] """清理 URL(移除追踪参数)"""
    cleaned_url = bookmark_analyzer.clean_url(req.url)
    return {
        "original_url": req.url,
        "cleaned_url": cleaned_url,
        "changed": req.url != cleaned_url
    }


# ── AI Configuration ───────────────────────────────────────────────────
@router.get("/ai/config")
def get_ai_config_status():
    """Get AI ConfigurationState"""
    config = get_ai_config()
    return config.to_dict()


@router.post("/ai/config/reload")
def reload_ai_config_endpoint():
    # [CN] """重新加载 AI 配置"""
    from aigard.bookmarks import reload_ai_config
    config = reload_ai_config()
    return {
        # [CN] "message": "AI 配置已重新加载",
        "config": config.to_dict()
    }


# [CN] # ── 新功能:浏览器状态检测 ────────────────────────────────────
class BrowserStateRequest(BaseModel):
    browser: str


@router.post("/state/check")
def check_browser_state(req: BrowserStateRequest):
    # [CN] """检测浏览器运行状态"""
    strategy = state_detector.get_modification_strategy(req.browser)
    return {
        "browser": req.browser,
        "state": strategy
    }


@router.get("/state/all")
def get_all_browsers_state():
    # [CN] """获取所有浏览器状态"""
    status = state_detector.get_all_browsers_status()
    return {
        "browsers": status
    }


# [CN] # ── 新功能:智能修复 ──────────────────────────────────────────
class SmartFixRequest(BaseModel):
    browser: str


@router.post("/fix/plan")
def generate_fix_plan(req: SmartFixRequest):
    # [CN] """生成智能修复计划"""
    if req.browser not in bookmark_manager.detected_browsers:
        raise HTTPException(status_code=404, detail=f"浏览器 {req.browser} 未检测到")

    # [CN] 检查浏览器状态
    strategy = state_detector.get_modification_strategy(req.browser)
    if not strategy['safe']:
        return {
            "browser": req.browser,
            "can_proceed": False,
            "warning": strategy['message'],
            "recommendation": strategy['recommendation']
        }

    # [CN] 读取书签
    bookmarks_data = bookmark_manager.read_bookmarks(req.browser)
    if not bookmarks_data:
        raise HTTPException(status_code=500, detail=f"读取 {req.browser} 书签失败")

    # [CN] 生成修复计划
    plan = bookmark_fixer.generate_smart_fix_plan(bookmarks_data)

    return {
        "browser": req.browser,
        "can_proceed": True,
        "plan": plan
    }


class ExecuteFixRequest(BaseModel):
    browser: str
    operations: List[dict]


@router.post("/fix/execute")
def execute_fix(req: ExecuteFixRequest):
    # [CN] """执行修复操作"""
    if req.browser not in bookmark_manager.detected_browsers:
        raise HTTPException(status_code=404, detail=f"浏览器 {req.browser} 未检测到")

    # [CN] # 再次检查浏览器状态
    strategy = state_detector.get_modification_strategy(req.browser)
    if not strategy['safe']:
        raise HTTPException(
            status_code=400,
            # [CN] detail=f"浏览器正在运行,无法安全修改。{strategy['recommendation']}"
        )

    # ExecuteModify
    result = bookmark_modifier.modify(req.browser, req.operations)

    return {
        "browser": req.browser,
        "result": result
    }


# [CN] # ── 新功能:备份管理 ──────────────────────────────────────────
@router.get("/backups")
def list_backups(browser: Optional[str] = None, limit: int = 20):
    # [CN] """列出备份"""
    backups = backup_manager.list_backups(browser, limit)
    return {
        "backups": backups,
        "count": len(backups)
    }


class RestoreBackupRequest(BaseModel):
    browser: str
    backup_id: str


@router.post("/backups/restore")
def restore_backup(req: RestoreBackupRequest):
    """RestoreBackup"""
    from pathlib import Path

    if req.browser not in bookmark_manager.detected_browsers:
        raise HTTPException(status_code=404, detail=f"浏览器 {req.browser} 未检测到")

    # [CN] # 检查浏览器状态
    strategy = state_detector.get_modification_strategy(req.browser)
    if not strategy['safe']:
        raise HTTPException(
            status_code=400,
            # [CN] detail=f"浏览器正在运行,无法恢复备份。{strategy['recommendation']}"
        )

    # RestoreBackup
    target_path = Path(bookmark_modifier.BROWSER_PATHS[req.browser]).expanduser()
    success = backup_manager.restore_backup(req.backup_id, target_path)

    if not success:
        raise HTTPException(status_code=500, detail="RestoreBackupFailure")

    return {
        "browser": req.browser,
        "backup_id": req.backup_id,
        # [CN] "message": "备份已恢复,请重启浏览器查看效果"
    }


# [CN] # ── 新功能:操作历史 ──────────────────────────────────────────
@router.get("/history")
def get_operation_history(browser: Optional[str] = None, limit: int = 20):
    # [CN] """获取操作历史"""
    history = operation_log.get_history(browser, limit)
    return {
        "history": history,
        "count": len(history)
    }
