import pathlib
from datetime import date

import pandas as pd
from fastapi import APIRouter
from fastapi.params import Depends, Query
from sqlalchemy import select, and_, text
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import FileResponse

from child_tracker_auth import schemas
from child_tracker_auth.db.base import LogTable, FileTable
from child_tracker_auth.db.dependencies import get_db_session
from child_tracker_auth.schemas import log_type_values
from child_tracker_auth.security.oauth2 import get_current_member
from child_tracker_auth.settings import settings
from child_tracker_auth.web.api.const import date_from_default, date_to_default

router = APIRouter(
    prefix="/devices",
    tags=["Devices"],
    dependencies=(
        [Depends(get_current_member)] if settings.environment == "prod" else None
    ),
)


@router.get("/{id}/logs", response_model=list[schemas.PydanticLog])
async def get_device_logs(
    id: int,
    offset: int = 0,
    limit: int = 100,
    date_from: date = date_from_default,
    date_to: date = date_to_default,
    log_type: str | None = Query(None, enum=log_type_values),
    db: AsyncSession = Depends(get_db_session),
):
    op_and = [LogTable.device_id == id, LogTable.date.between(date_from, date_to)]
    if log_type is not None:
        op_and.append(LogTable.log_type == log_type)
    q = select(LogTable).filter(and_(*op_and))
    q = q.offset(offset).limit(limit)
    rq = await db.execute(q)
    r = rq.scalars().all()
    logs = [schemas.PydanticLog(**x.__dict__) for x in r]
    return logs


@router.get("/{id}/files", response_model=list[schemas.PydanticFile])
async def get_device_files(
    id: int,
    offset: int = 0,
    limit: int = 100,
    date_from: date = date_from_default,
    date_to: date = date_to_default,
    db: AsyncSession = Depends(get_db_session),
):
    q = select(FileTable).filter(
        and_(FileTable.device_id == id, FileTable.time.between(date_from, date_to))
    )
    q = q.offset(offset).limit(limit)
    rq = await db.execute(q)
    r = rq.scalars().all()
    logs = [schemas.PydanticFile(**x.__dict__) for x in r]
    return logs


@router.get("/{device_id}/file/{file_id}", response_class=FileResponse)
async def download_device_files(
    device_id: int,
    file_id: int,
    db: AsyncSession = Depends(get_db_session),
):
    q = select(FileTable).filter(
        and_(FileTable.id == file_id, FileTable.device_id == device_id)
    )
    rq = await db.execute(q)
    r = rq.scalars().first()
    m = schemas.PydanticFile(**r.__dict__)
    file_path = pathlib.Path(settings.public_dir_path).parent.joinpath(
        str(m.path).lstrip("/")
    )
    return FileResponse(file_path, media_type=m.type, filename=m.name)


@router.get("/{id}/calls", response_model=dict[str, list[schemas.PhoneCall]])
async def get_device_calls(
    id: int,
    offset: int = 0,
    limit: int = 100,
    date_from: date = date_from_default,
    date_to: date = date_to_default,
    db: AsyncSession = Depends(get_db_session),
):
    q = text(
        f"""
    select
        l.name as name,
        l.log_type as type,
        l.duration as duration,
        l.`date` as date
    from
        logs l
    join devices d on
        d.id = l.device_id
    where
        d.id = :device_id
        and l.log_type in ('in_call', 'out_call', 'out_sms')
        and (l.`date` between :date_from and :date_to)
    limit :limit OFFSET :offset
    """
    )
    rq = await db.execute(
        q,
        {
            "limit": limit,
            "offset": offset,
            "device_id": id,
            "date_from": date_from.__str__(),
            "date_to": date_to.__str__(),
        },
    )
    r = rq.mappings().all()
    phone_data = [schemas.PhoneCall(**x) for x in r]
    phone_data_df = pd.DataFrame(r)
    phone_data_df_by_date = phone_data_df.groupby("date").apply(
        lambda g: g.to_dict(orient="records")).to_dict()
    calls = {k.__str__(): [schemas.PhoneCall(**vv) for vv in v] for k, v in
             phone_data_df_by_date.items()}
    return calls
