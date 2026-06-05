"""Agent 成长工作区 — 薄展示层（逻辑在 daozhu/growth.py）"""

import sys
from pathlib import Path
from fastapi import APIRouter, HTTPException

# 确保能 import daozhu 核心模块
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

router = APIRouter()


@router.get("/reports")
async def list_reports():
    """获取成长报告列表"""
    from daozhu.growth import get_growth_reports
    return {"reports": get_growth_reports()}


@router.get("/idle-history")
async def idle_work_history():
    """获取 AI 自主工作历史（#073）"""
    from daozhu.idle_worker import get_report_history, get_idle_minutes
    return {
        "reports": get_report_history(limit=20),
        "current_idle_minutes": round(get_idle_minutes(), 1),
    }


@router.get("/stats")
async def get_stats():
    """获取工具健康数据"""
    from daozhu.tool_log_db import get_tool_stats, get_stale_tools
    return {"tool_stats": get_tool_stats(days=7), "stale_tools": get_stale_tools(days=30)}


@router.post("/run")
async def trigger_growth():
    """手动触发一次成长"""
    from daozhu.growth import run_growth
    result = run_growth()
    return {"success": True, **result}


@router.post("/suggestions/{report_id}/confirm")
async def confirm(report_id: int, body: dict):
    """确认执行建议"""
    from daozhu.growth import confirm_suggestion
    index = body.get("index", 0)
    result = confirm_suggestion(report_id, index)
    return {"success": True, "result": result}
