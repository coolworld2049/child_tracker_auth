from fastapi.routing import APIRouter

from child_tracker_auth.web.api import auth, member, devices, settings, utils, ws

api_router = APIRouter(prefix="/api")
api_router.include_router(auth.router)
api_router.include_router(member.router)
api_router.include_router(devices.router)
api_router.include_router(settings.router)
api_router.include_router(utils.router)

ws_router = APIRouter(prefix="/ws")
ws_router.include_router(ws.router)
