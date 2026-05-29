from .store import router as store_router
from .pets import router as pets_router
from .interact import router as interact_router

__all__ = ["store_router", "pets_router", "interact_router"]
