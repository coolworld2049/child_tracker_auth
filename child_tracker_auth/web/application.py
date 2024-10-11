from cashews.contrib.fastapi import (
    CacheDeleteMiddleware,
    CacheRequestControlMiddleware,
    CacheEtagMiddleware,
)
from fastapi import FastAPI
from fastapi.responses import UJSONResponse
from starlette.middleware.cors import CORSMiddleware

from child_tracker_auth.log import configure_logging
from child_tracker_auth.middleware import HTTPErrorMiddleware
from child_tracker_auth.settings import settings
from child_tracker_auth.web.api.router import api_router, ws_router
from child_tracker_auth.web.lifespan import lifespan_setup


def get_app() -> FastAPI:
    configure_logging()
    app = FastAPI(
        title=settings.project_name or "API",
        lifespan=lifespan_setup,
        default_response_class=UJSONResponse,
    )
    app.include_router(router=api_router)
    app.include_router(router=ws_router)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(HTTPErrorMiddleware)
    app.add_middleware(CacheDeleteMiddleware)
    app.add_middleware(CacheEtagMiddleware)
    app.add_middleware(CacheRequestControlMiddleware)
    return app
