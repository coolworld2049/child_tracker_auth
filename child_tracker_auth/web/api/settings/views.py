from typing import Literal

from fastapi import APIRouter
from fastapi.params import Depends, Query
from loguru import logger
from sqlalchemy import select, and_, func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status
from starlette.exceptions import HTTPException

from child_tracker_auth import schemas
from child_tracker_auth.db.base import SettingsTable
from child_tracker_auth.db.dependencies import get_db_session
from child_tracker_auth.security.oauth2 import get_current_member
from child_tracker_auth.settings import settings

router = APIRouter(
    prefix="/settings",
    tags=["Settings"],
    dependencies=(
        [Depends(get_current_member)] if settings.environment == "prod" else None
    ),
)


@router.get("/keys", response_model=list[schemas.PydanticSettingsWithTypeKey])
async def get_settings_keys(
    object_type: Literal["member", "section"],
    db: AsyncSession = Depends(get_db_session),
):
    q = select(SettingsTable.key.distinct().label("key"), SettingsTable.value).filter(
        and_(
            SettingsTable.object_type == object_type,
        )
    )
    r = await db.execute(q)
    mp = r.mappings().all()
    unique_keys: set[str] = set()
    keys: list[schemas.PydanticSettingsWithTypeKey] = []
    for x in mp:
        if x["key"] in unique_keys:
            continue
        value = schemas.convert_value_type(x["value"])
        data_type = None
        if value is not None:
            if value == "":
                data_type = "str"
            else:
                data_type = (
                    str(type(value.item())).replace("<class '", "").replace("'>", "")
                )
        keys.append(
            schemas.PydanticSettingsWithTypeKey(key=x["key"], data_type=data_type)
        )
        unique_keys.add(x["key"])

    return keys


@router.get("/", response_model=list[schemas.PydanticSettingsWithType])
async def get_settings(
    object_id: int,
    object_type: Literal["member", "section"],
    key: str | None = Query(None, description="Full text search"),
    db: AsyncSession = Depends(get_db_session),
):
    and_f = []
    if key:
        and_f.append(SettingsTable.key.ilike(f"%{key}%"))
    q = select(SettingsTable).filter(
        and_(
            SettingsTable.object_id == object_id,
            SettingsTable.object_type == object_type,
            *and_f,
        )
    )
    r = await db.execute(q)
    rq = r.scalars().all()
    settings = [schemas.PydanticSettingsWithType(**x.__dict__) for x in rq]
    return settings


@router.post("/upsert", response_model=schemas.PydanticSettingsWithType)
async def upsert_setting(
    key: str,
    value: str,
    object_id: int,
    object_type: str = Query("app", enum=["member", "section"]),
    group: str = Query("app", enum=["app", "other"]),
    db: AsyncSession = Depends(get_db_session),
):
    q = select(SettingsTable).filter(
        and_(
            SettingsTable.key == key,
            SettingsTable.object_id == object_id,
            SettingsTable.object_type == object_type,
            SettingsTable.group == group,
        )
    )
    r = await db.execute(q)
    setting = r.scalars().first()
    date_now = func.now()
    if not setting:
        setting = SettingsTable(
            object_id=object_id,
            object_type=object_type,
            group=group,
            key=key,
            value=value,
            created_at=date_now,
        )
    else:
        setting.value = value
        setting.updated_at = func.now()
    try:
        db.add(setting)
        await db.commit()
        await db.refresh(setting)
    except SQLAlchemyError as e:
        logger.error(e)
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.__str__())

    return schemas.PydanticSettingsWithType(**setting.__dict__)


@router.put("/", response_model=schemas.PydanticSettingsWithType)
async def update_setting(
    id: int,
    value: str,
    db: AsyncSession = Depends(get_db_session),
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

    return schemas.PydanticSettingsWithType(**setting.__dict__)
