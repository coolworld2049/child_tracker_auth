from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.crud import create_user
from app.schemas import UserCreate, UserRead, UserUpdate
from app.settings import settings
from app.users import (
    auth_backend,
    fastapi_users,
)


@asynccontextmanager
async def lifespan(app):
    await create_user(settings.ADMIN_USERNAME, settings.ADMIN_PASSWORD)
    yield


app = FastAPI(lifespan=lifespan)

app.include_router(
    fastapi_users.get_auth_router(auth_backend), prefix="/auth/jwt", tags=["auth"]
)
app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_reset_password_router(),
    prefix="/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_verify_router(UserRead),
    prefix="/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
)
