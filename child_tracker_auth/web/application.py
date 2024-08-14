from fastapi import FastAPI
from fastapi.responses import UJSONResponse

from child_tracker_auth.log import configure_logging
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
        title="child_tracker_auth",
        lifespan=lifespan_setup,
        default_response_class=UJSONResponse,
    )

    # Main router for the API.
    app.include_router(router=api_router, prefix="/api")

    return app
