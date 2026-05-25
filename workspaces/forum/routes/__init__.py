"""路由汇总"""
from fastapi import APIRouter
from .issues import router as issues_router

router = APIRouter()
router.include_router(issues_router, prefix="/issues", tags=["issues"])
