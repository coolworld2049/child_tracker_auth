from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from child_tracker_auth.settings import settings
from child_tracker_auth.storage.dependencies import (
    on_startup_storage,
    on_shutdown_storage,
)

redis_client = Redis(
    host=settings.redis_host,
    port=settings.redis_port,
    username=settings.redis_user,
    password=settings.redis_password,
    db=settings.redis_websocket_db,
)


def create_session_factory():
    engine = create_async_engine(str(settings.db_url), echo=settings.db_echo)
    session_factory = async_sessionmaker(
        engine,
        expire_on_commit=False,
    )
    return engine, session_factory


def _setup_db(app: FastAPI) -> None:  # pragma: no cover
    engine, session_factory = create_session_factory()
    app.state.db_engine = engine
    app.state.db_session_factory = session_factory


@asynccontextmanager
async def lifespan_setup(
    app: FastAPI,
) -> AsyncGenerator[None, None]:  # pragma: no cover
    app.middleware_stack = None
    _setup_db(app)
    await on_startup_storage(app=app)
    await redis_client.ping()

    app.middleware_stack = app.build_middleware_stack()

    yield

    await app.state.db_engine.dispose()
    await on_shutdown_storage(app)
