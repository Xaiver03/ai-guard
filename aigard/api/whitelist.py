"""
# [CN] 白名单管理 API
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/whitelist", tags=["whitelist"])


class AddProcessNameRequest(BaseModel):
    name: str


class AddCommandKeywordRequest(BaseModel):
    keyword: str


class AddPidRequest(BaseModel):
    pid: int


@router.get("")
async def get_whitelist():
    # [CN] """获取所有白名单条目"""
    import main as _main_mod
    return _main_mod.whitelist.get_all()


@router.post("/process_name")
async def add_process_name(req: AddProcessNameRequest):
    # [CN] """添加进程名到白名单"""
    import main as _main_mod
    success = _main_mod.whitelist.add_process_name(req.name)
    if not success:
        raise HTTPException(status_code=400, detail="进程名已存在于白名单中")
    return {"success": True, "message": f"已将 {req.name} 添加到白名单"}


@router.delete("/process_name/{name}")
async def remove_process_name(name: str):
    # [CN] """从白名单移除进程名"""
    import main as _main_mod
    success = _main_mod.whitelist.remove_process_name(name)
    if not success:
        raise HTTPException(status_code=404, detail="Process name not in whitelist")
    return {"success": True, "message": f"Removed {name} from whitelist"}


@router.post("/command_keyword")
async def add_command_keyword(req: AddCommandKeywordRequest):
    # [CN] """添加命令行关键字到白名单"""
    import main as _main_mod
    success = _main_mod.whitelist.add_command_keyword(req.keyword)
    if not success:
        raise HTTPException(status_code=400, detail="关键字已存在于白名单中")
    return {"success": True, "message": f"已将关键字 {req.keyword} 添加到白名单"}


@router.delete("/command_keyword/{keyword}")
async def remove_command_keyword(keyword: str):
    """从白名单移除命令行关键字"""
    import main as _main_mod
    success = _main_mod.whitelist.remove_command_keyword(keyword)
    if not success:
        raise HTTPException(status_code=404, detail="Keyword not in whitelist")
    return {"success": True, "message": f"Removed keyword {keyword} from whitelist"}


@router.post("/pid")
async def add_pid(req: AddPidRequest):
    # [CN] """添加 PID 到白名单(临时,重启后失效)"""
    import main as _main_mod
    success = _main_mod.whitelist.add_pid(req.pid)
    if not success:
        raise HTTPException(status_code=400, detail="PID 已存在于白名单中")
    return {"success": True, "message": f"已将 PID {req.pid} 添加到白名单(临时)"}


@router.delete("/pid/{pid}")
async def remove_pid(pid: int):
    # [CN] """从白名单移除 PID"""
    import main as _main_mod
    success = _main_mod.whitelist.remove_pid(pid)
    if not success:
        raise HTTPException(status_code=404, detail="PID 不在白名单中")
    return {"success": True, "message": f"已将 PID {pid} 从白名单移除"}
