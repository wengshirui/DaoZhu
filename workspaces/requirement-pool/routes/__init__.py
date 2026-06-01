"""路由汇总"""
from fastapi import APIRouter
from .systems import router as systems_router
from .requirements import router as requirements_router

router = APIRouter()
router.include_router(systems_router, prefix="/systems", tags=["systems"])
router.include_router(requirements_router, prefix="/requirements", tags=["requirements"])
