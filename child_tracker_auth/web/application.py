from fastapi import FastAPI
from fastapi.responses import UJSONResponse

from child_tracker_auth.log import configure_logging
from child_tracker_auth.middleware import HTTPErrorMiddleware
from child_tracker_auth.settings import settings
from child_tracker_auth.web.api.router import api_router
from child_tracker_auth.web.lifespan import lifespan_setup


def get_app() -> FastAPI:
    """
    Get FastAPI application.

    This is the main constructor of an application.

    :return: application.
    """
    configure_logging()
    app = FastAPI(
        title=settings.project_name or "API",
        lifespan=lifespan_setup,
        default_response_class=UJSONResponse,
    )

    # Main router for the API.
    app.include_router(router=api_router, prefix="/api")
    app.add_middleware(HTTPErrorMiddleware)
    return app
