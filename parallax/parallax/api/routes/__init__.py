"""
Export routers.
"""

from parallax.api.routes.analyze import router as analyze_router
from parallax.api.routes.history import router as history_router
from parallax.api.routes.status import router as status_router

__all__ = ["analyze_router", "history_router", "status_router"]
