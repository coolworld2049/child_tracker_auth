from datetime import date

from dateutil.relativedelta import relativedelta
from fastapi import APIRouter
from fastapi.params import Depends, Query
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from child_tracker_auth import schemas
from child_tracker_auth.db.base import LogTable, engine, FileTable
from child_tracker_auth.db.dependencies import get_db_session
from child_tracker_auth.db.enums import get_enum_values
from child_tracker_auth.security.oauth2 import get_current_member
from child_tracker_auth.settings import settings

router = APIRouter(
    prefix="/devices",
    tags=["Devices"],
    dependencies=(
        [Depends(get_current_member)] if settings.environment == "prod" else None
    ),
)

date_from_default: date = date.today() - relativedelta(months=1)
date_to_default: date = date.today() + relativedelta(months=1)

log_type_values = get_enum_values(
    engine=engine, table_name="logs", column_name="log_type"
)


@router.get("/{id}/logs", response_model=list[schemas.PydanticLog])
async def get_device_logs(
    id: int,
    date_from: date = date_from_default,
    date_to: date = date_to_default,
    log_type: str | None = Query(None, enum=log_type_values),
    db: AsyncSession = Depends(get_db_session),
):
    op_and = [LogTable.device_id == id, LogTable.date.between(date_from, date_to)]
    if log_type is not None:
        op_and.append(LogTable.log_type == log_type)
    q = select(LogTable).filter(and_(*op_and))
    rq = await db.execute(q)
    r = rq.scalars().all()
    logs = [schemas.PydanticLog(**x.__dict__) for x in r]
    return logs


@router.get("/{id}/files", response_model=list[schemas.PydanticFile])
async def get_device_files(
    id: int,
    date_from: date = date_from_default,
    date_to: date = date_to_default,
    db: AsyncSession = Depends(get_db_session),
):
    q = select(FileTable).filter(
        and_(FileTable.device_id == id, FileTable.time.between(date_from, date_to))
    )
    rq = await db.execute(q)
    r = rq.scalars().all()
    logs = [schemas.PydanticFile(**x.__dict__) for x in r]
    return logs
