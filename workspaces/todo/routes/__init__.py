"""路由汇总"""

from fastapi import APIRouter
from .tasks import router as tasks_router
from .projects import router as projects_router
from .tags import router as tags_router

router = APIRouter()
router.include_router(tasks_router, prefix="/tasks", tags=["tasks"])
router.include_router(projects_router, prefix="/projects", tags=["projects"])
router.include_router(tags_router, prefix="/tags", tags=["tags"])
