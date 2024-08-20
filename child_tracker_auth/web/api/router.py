from fastapi.routing import APIRouter

from child_tracker_auth.web.api import auth, member, devices, settings

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(member.router)
api_router.include_router(devices.router)
api_router.include_router(settings.router)
