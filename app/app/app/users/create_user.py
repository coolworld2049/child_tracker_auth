import contextlib

from fastapi_users.exceptions import UserAlreadyExists
from loguru import logger

from app.schemas import UserCreate
from .database import get_user_db
from .manager import get_user_manager
from ..db import get_async_session

get_async_session_context = contextlib.asynccontextmanager(get_async_session)
get_user_db_context = contextlib.asynccontextmanager(get_user_db)
get_user_manager_context = contextlib.asynccontextmanager(get_user_manager)


async def create_user(email: str, password: str, is_superuser: bool = False):
    try:
        async with get_async_session_context() as session:
            async with get_user_db_context(session) as user_db:
                async with get_user_manager_context(user_db) as user_manager:
                    user = await user_manager.create(
                        UserCreate(
                            email=email,
                            password=password,
                            is_superuser=is_superuser,
                            is_verified=True,
                            is_active=True,
                        )
                    )
                    logger.warning(f"User created {user}")
    except UserAlreadyExists:
        logger.warning(f"User {email} already exists")
