from app.routers.auth import router as auth_router
from app.routers.inspections import router as inspections_router
from app.routers.dashboard import router as dashboard_router

__all__ = ["auth_router", "inspections_router", "dashboard_router"]
