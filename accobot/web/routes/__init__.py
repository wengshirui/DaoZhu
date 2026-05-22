"""AccoBot Web Routes — modular API routers.

Each sub-module defines an APIRouter that is registered here.
"""

from fastapi import FastAPI

from .config import router as config_router
from .files import router as files_router
from .chat import router as chat_router
from .ledger import router as ledger_router
from .mcp import router as mcp_router
from .todos import router as todos_router


def register_routes(app: FastAPI):
    """Register all API routers on the FastAPI app."""
    app.include_router(config_router)
    app.include_router(files_router)
    app.include_router(chat_router)
    app.include_router(ledger_router)
    app.include_router(mcp_router)
    app.include_router(todos_router)
