from typing import AsyncGenerator
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.settings import settings

SQLALCHEMY_ENGINE_OPTIONS = {
    "pool_pre_ping": True,
    "echo": True if settings.IS_DEBUG else False,
}
async_engine = create_async_engine(
    settings.async_database_url, **SQLALCHEMY_ENGINE_OPTIONS
)
sync_engine = create_engine(settings.sync_database_url, **SQLALCHEMY_ENGINE_OPTIONS)
async_session_maker = async_sessionmaker(async_engine, expire_on_commit=False)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session
