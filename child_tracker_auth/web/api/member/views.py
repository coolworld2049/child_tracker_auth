from datetime import date

from dateutil.relativedelta import relativedelta
from fastapi import APIRouter
from fastapi.params import Depends
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from child_tracker_auth import schemas
from child_tracker_auth.db.base import DeviceTable
from child_tracker_auth.db.dependencies import get_db_session
from child_tracker_auth.security.oauth2 import get_current_member

router = APIRouter(prefix="/members", tags=["Members"])

date_from_default: date = date.today() - relativedelta(months=1)
date_to_default: date = date.today() + relativedelta(months=1)


@router.get("/me", response_model=schemas.PydanticMember)
async def get_member_me(
    current_member: schemas.PydanticMember = Depends(get_current_member),
):
    return schemas.PydanticMember(**current_member.__dict__)


@router.get("/me/devices", response_model=list[schemas.PydanticDevice])
async def get_member_devices(
    date_from: date = date_from_default,
    date_to: date = date_to_default,
    db: AsyncSession = Depends(get_db_session),
    current_member: schemas.PydanticMember = Depends(get_current_member),
):
    q = select(DeviceTable).where(DeviceTable.member_id == current_member.id)
    q = q.filter(and_(DeviceTable.time.between(date_from, date_to)))

    r = await db.execute(q)
    devices = [schemas.PydanticDevice(**x.__dict__) for x in r.scalars().all()]
    return devices
