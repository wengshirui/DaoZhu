"""路由注册 — app.py 中调用 register_routers(app) 即可注册所有路由"""
from .page_routes import router as page_router
from .workspace_routes import router as workspace_router
from .chat_routes import router as chat_router
from .misc_routes import router as misc_router


def register_routers(app):
    """将各功能模块的路由注册到 FastAPI 实例"""
    app.include_router(page_router)
    app.include_router(workspace_router)
    app.include_router(chat_router)
    app.include_router(misc_router)
