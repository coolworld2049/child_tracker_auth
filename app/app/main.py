from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from app.auth.backend import auth_backend
from app.loguru_logger import configure_logging
from app.schemas import UserCreate, UserRead, UserUpdate
from app.settings import settings
from app.users.create_user import create_user
from app.users.manager import fastapi_users
from prestart import prestart

configure_logging(
    settings.LOG_LEVEL,
    access_log_path="access.log",
)


@asynccontextmanager
async def lifespan(app):
    await create_user(settings.ADMIN_USERNAME, settings.ADMIN_PASSWORD)
    yield


def get_application() -> FastAPI:
    application = FastAPI(title="child_tracker_auth")
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        expose_headers=["*"],
    )

    application.include_router(
        fastapi_users.get_auth_router(auth_backend), prefix="/auth/jwt", tags=["auth"]
    )
    application.include_router(
        fastapi_users.get_register_router(UserRead, UserCreate),
        prefix="/auth",
        tags=["auth"],
    )
    application.include_router(
        fastapi_users.get_reset_password_router(),
        prefix="/auth",
        tags=["auth"],
    )
    application.include_router(
        fastapi_users.get_verify_router(UserRead),
        prefix="/auth",
        tags=["auth"],
    )
    application.include_router(
        fastapi_users.get_users_router(UserRead, UserUpdate),
        prefix="/users",
        tags=["users"],
    )

    return application


app = get_application()

if __name__ == "__main__":
    prestart()
    uvicorn.run(
        "main:app",
        reload=False,
        host=settings.HOST,
        port=settings.PORT,
        access_log=False,
    )
