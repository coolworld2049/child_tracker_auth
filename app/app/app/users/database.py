from typing import AsyncGenerator

from fastapi import Depends
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_async_session
from app.models import User, OAuthAccount


async def get_user_db(
    session: AsyncSession = Depends(get_async_session),
) -> AsyncGenerator:
    yield SQLAlchemyUserDatabase(session, User, OAuthAccount)
