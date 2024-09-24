import random
from datetime import timedelta
from uuid import uuid4

from fastapi import APIRouter
from fastapi import Depends, HTTPException, status
from loguru import logger
from requests import HTTPError
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from starlette.requests import Request

from child_tracker_auth import schemas
from child_tracker_auth.db.base import MemberTable
from child_tracker_auth.db.dependencies import get_db_session
from child_tracker_auth.security.oauth2 import (
    create_access_refresh_token,
    get_current_member,
)
from child_tracker_auth.settings import settings
from child_tracker_auth.utils.sms import send_verification_sms

router = APIRouter(tags=["Auth"])


def send_sms_code(phone: str, code: int):
    try:
        send_verification_sms(to_phone=phone, code=code)
    except HTTPError as he:
        raise HTTPException(
            status_code=he.response.status_code, detail=he.response.text
        )


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.RegistrationUserRepsonse,
)
async def register(
    request: Request,
    user_credentials: schemas.PydanticMemberCreate,
    db: AsyncSession = Depends(get_db_session),
):
    check_query = select(MemberTable).filter(
        or_(
            MemberTable.phone == user_credentials.phone,
        )
    )
    check_result = await db.execute(check_query)
    check = check_result.scalars().first()

    if check is not None:
        raise HTTPException(
            detail="User is already registered", status_code=status.HTTP_409_CONFLICT
        )

    code = random.randint(1000, 9999)

    new_user = MemberTable(
        email=f"{uuid4().__str__()}@gmail.com",
        name=user_credentials.name,
        role=user_credentials.role,
        active=user_credentials.active,
        password="",
        password_pbkdf_hash="",
        phone=user_credentials.phone,
        code=code,
    )
    try:
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
    except SQLAlchemyError as e:
        logger.error(e)
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.__str__())

    if new_user.name != settings.google_play_member_name:
        send_sms_code(phone=new_user.phone, code=code)

    return schemas.RegistrationUserRepsonse(
        message="User registration successful. Please verify your phone number",
        data=schemas.PydanticMember(**new_user.__dict__),
    )


@router.post("/login", response_model=schemas.ResponseModel)
async def login(
    login_data: schemas.LoginModel,
    db: AsyncSession = Depends(get_db_session),
):
    user_query = select(MemberTable).filter(MemberTable.phone == login_data.phone)
    user_result = await db.execute(user_query)
    user = user_result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User does not exist",
        )

    code = random.randint(1000, 9999)
    try:
        user.code = code
        db.add(user)
        await db.commit()
        await db.refresh(user)
    except SQLAlchemyError as e:
        logger.error(e)
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.__str__())

    send_sms_code(phone=user.phone, code=code)

    return schemas.ResponseModel(message="Verification code sent successfully")


async def auth_member_by_sms(code: int, phone: str, db: AsyncSession):
    user_query = select(MemberTable).filter(MemberTable.phone == phone)
    user_result = await db.execute(user_query)
    user = user_result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if (
        user.name == settings.google_play_member_name
        and code == settings.google_play_member_code
        and phone == settings.google_play_member_phone
    ):
        user.code = code
        logger.warning("Granted access to Google Play Service for a fake account")

    if user.code != code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid code",
        )

    data = schemas.TokenData(user_id=user.id, phone=user.phone)

    access_token = create_access_refresh_token(
        data, expires_delta=timedelta(minutes=settings.access_token_expire_minutes)
    )
    refresh_token = create_access_refresh_token(
        data, expires_delta=timedelta(minutes=settings.refresh_token_expire_minutes)
    )

    try:
        user.code = None
        user.active = 1
        db.add(user)
        await db.commit()
        await db.refresh(user)
    except SQLAlchemyError as e:
        logger.error(e)
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.__str__())

    return schemas.TokenModel(access_token=access_token, refresh_token=refresh_token)


@router.post("/auth", response_model=schemas.TokenModel)
async def auth(
    auth_data: schemas.AuthModel,
    db: AsyncSession = Depends(get_db_session),
):
    token_data = await auth_member_by_sms(
        phone=auth_data.phone, code=auth_data.code, db=db
    )
    return token_data


@router.post("/auth/refresh_token", response_model=schemas.TokenModel)
async def auth(
    form_data: schemas.RefreshTokenModel,
    db: AsyncSession = Depends(get_db_session),
):
    user = await get_current_member(token=form_data.refresh_token, db=db)

    data = schemas.TokenData(user_id=user.id, phone=user.phone)

    access_token = create_access_refresh_token(
        data, expires_delta=timedelta(minutes=settings.access_token_expire_minutes)
    )
    refresh_token = create_access_refresh_token(
        data, expires_delta=timedelta(minutes=settings.refresh_token_expire_minutes)
    )

    return schemas.TokenModel(access_token=access_token, refresh_token=refresh_token)
