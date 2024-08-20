from typing import Literal

from fastapi import APIRouter
from fastapi.params import Depends, Query
from loguru import logger
from sqlalchemy import select, and_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status
from starlette.exceptions import HTTPException

from child_tracker_auth import schemas
from child_tracker_auth.db.base import SettingsTable
from child_tracker_auth.db.dependencies import get_db_session
from child_tracker_auth.security.oauth2 import get_current_member

router = APIRouter(prefix="/settings", tags=["Settings"])


@router.get("/", response_model=list[schemas.PydanticSettings])
async def get_settings(
    object_id: int,
    object_type: Literal["member", "section"],
    key: str | None = Query(None, description="Full text search"),
    db: AsyncSession = Depends(get_db_session),
    current_member: schemas.PydanticMember = Depends(get_current_member),
):
    q = select(SettingsTable).filter(
        and_(
            SettingsTable.object_id == object_id,
            SettingsTable.object_type == object_type,
            SettingsTable.key.ilike(f"%{key}%") if key else None,
        )
    )
    r = await db.execute(q)
    settings = [schemas.PydanticSettings(**x.__dict__) for x in r.scalars().all()]
    return settings


@router.put("/", response_model=schemas.PydanticSettings)
async def update_setting(
    id: int,
    value: str,
    db: AsyncSession = Depends(get_db_session),
    current_member: schemas.PydanticMember = Depends(get_current_member),
):
    q = select(SettingsTable).filter(SettingsTable.id == id)
    r = await db.execute(q)
    setting = r.scalars().first()

    try:
        setting.value = value
        db.add(setting)
        await db.commit()
        await db.refresh(setting)
    except SQLAlchemyError as e:
        logger.error(e)
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.__str__())

    return schemas.PydanticSettings(**setting.__dict__)
