from fastapi import APIRouter
from fastapi.params import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.exceptions import HTTPException

from child_tracker_auth import schemas
from child_tracker_auth.db.base import DeviceTable, MemberAccountsTable
from child_tracker_auth.db.dependencies import get_db_session
from child_tracker_auth.security.oauth2 import get_current_member

router = APIRouter(prefix="/members", tags=["Members"])


@router.get("/me", response_model=schemas.PydanticMember)
async def get_member_me(
    current_member: schemas.PydanticMember = Depends(get_current_member),
):
    return schemas.PydanticMember(**current_member.__dict__)


@router.get("/me/devices", response_model=list[schemas.PydanticDevice])
async def get_member_devices(
    offset: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db_session),
    current_member: schemas.PydanticMember = Depends(get_current_member),
):
    q = select(DeviceTable).where(DeviceTable.member_id == current_member.id)
    q = q.offset(offset).limit(limit)
    r = await db.execute(q)
    devices = [schemas.PydanticDevice(**x.__dict__) for x in r.scalars().all()]
    return devices


@router.get("/me/account", response_model=schemas.MemberAccount)
async def get_member_me_account(
    db: AsyncSession = Depends(get_db_session),
    current_member: schemas.PydanticMember = Depends(get_current_member),
):
    q = select(MemberAccountsTable).where(
        MemberAccountsTable.member_id == current_member.id)
    r = await db.execute(q)
    rq = r.scalars().first()
    if not rq:
        return HTTPException(status_code=404)
    account = schemas.MemberAccount(**rq.__dict__)
    return account
