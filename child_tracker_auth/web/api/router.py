from fastapi.routing import APIRouter

from child_tracker_auth.web.api import monitoring

api_router = APIRouter()
api_router.include_router(monitoring.router)
