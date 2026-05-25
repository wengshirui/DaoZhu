"""路由汇总"""
from fastapi import APIRouter
from .companies import router as companies_router
from .accounts import router as accounts_router
from .vouchers import router as vouchers_router

router = APIRouter()
router.include_router(companies_router, prefix="/companies", tags=["companies"])
router.include_router(accounts_router, prefix="/accounts", tags=["accounts"])
router.include_router(vouchers_router, prefix="/vouchers", tags=["vouchers"])
