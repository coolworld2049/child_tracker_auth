from typing import Literal

from fastapi import APIRouter
from fastapi.params import Depends, Query
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from child_tracker_auth import schemas
from child_tracker_auth.db.base import SettingsTable
from child_tracker_auth.db.dependencies import get_db_session

router = APIRouter(prefix="/settings", tags=["Settings"])


@router.get("/", response_model=list[schemas.PydanticSettings])
async def get_settings(
    object_id: int,
    object_type: Literal["member", "section"],
    key: str | None = Query(None, description="Full text search"),
    db: AsyncSession = Depends(get_db_session),
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
