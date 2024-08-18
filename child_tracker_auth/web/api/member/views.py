from datetime import date

from fastapi import APIRouter, Depends
from fastapi.params import Depends
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from child_tracker_auth import schemas
from child_tracker_auth.db.base import DeviceTable, LogTable
from child_tracker_auth.db.dependencies import get_db_session
from child_tracker_auth.security.oauth2 import get_current_user

router = APIRouter(dependencies=[Depends(get_current_user)])

date_from_default: date = date.today().replace(day=date.today().day - 1)
date_to_default: date = date.today().replace(day=date.today().day + 1)


@router.get("/members/{id}/devices", response_model=list[schemas.PydanticDevice])
async def read_member_devices(
    id: int,
    date_from: date = date_from_default,
    date_to: date = date_to_default,
    db: AsyncSession = Depends(get_db_session),
):
    q = (
        select(DeviceTable)
        .where(DeviceTable.member_id == id)
        .filter(and_(DeviceTable.time.between(date_from, date_to)))
    )
    r = await db.execute(q)
    devices = [schemas.PydanticDevice(**x.__dict__) for x in r.scalars().all()]
    return devices


@router.get("/devices/{id}", response_model=list[schemas.PydanticLog])
async def read_member_device_logs(
    id: int,
    date_from: date = date_from_default,
    date_to: date = date_to_default,
    db: AsyncSession = Depends(get_db_session),
):
    q = select(LogTable).where(LogTable.device_id == id)
    r = await db.execute(q)
    logs = [schemas.PydanticLog(**x.__dict__) for x in r.scalars().all()]
    return logs
