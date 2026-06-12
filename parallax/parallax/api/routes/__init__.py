"""
Export routers.
"""

from parallax.api.routes.analyze import router as analyze_router
from parallax.api.routes.dynamic import router as dynamic_router
from parallax.api.routes.graph import router as graph_router
from parallax.api.routes.history import router as history_router
from parallax.api.routes.hunt import router as hunt_router
from parallax.api.routes.results import router as results_router
from parallax.api.routes.status import router as status_router

__all__ = [
    "analyze_router",
    "status_router",
    "history_router",
    "dynamic_router",
    "graph_router",
    "hunt_router",
    "results_router",
]
