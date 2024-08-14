from fastapi.routing import APIRouter

from child_tracker_auth.web.api import auth

api_router = APIRouter()
api_router.include_router(auth.router)
