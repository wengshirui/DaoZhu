"""定时任务 API 路由（代理到平台调度器）"""

from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.get("/tasks")
async def list_tasks():
    """列出所有定时任务"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
    from daozhu.scheduler import list_tasks
    return {"tasks": list_tasks()}


@router.get("/tasks/{task_id}/runs")
async def get_runs(task_id: int):
    """获取执行历史"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
    from daozhu.scheduler import get_task_runs
    return {"runs": get_task_runs(task_id)}
