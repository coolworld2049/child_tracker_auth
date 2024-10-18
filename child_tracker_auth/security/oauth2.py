from datetime import timedelta, datetime, timezone
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader
from jose import JWTError, jwt
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from child_tracker_auth import schemas
from child_tracker_auth.db.base import MemberTable
from child_tracker_auth.db.dependencies import get_db_session
from child_tracker_auth.settings import settings

token_header = APIKeyHeader(
    name="Authorization", description="access_token", scheme_name="Access Token Auth"
)


def create_access_refresh_token(
    data: schemas.TokenData, expires_delta: timedelta | None = None
):
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    data.exp = expire
    encoded_jwt = jwt.encode(
        data.model_dump(), settings.secret_key, algorithm=settings.algorithm
    )
    return encoded_jwt


def verify_access_token(token: str, credential_exception):
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=settings.algorithm)
        if id is None:
            raise credential_exception
        return schemas.TokenData(**payload)
    except JWTError:
        raise credential_exception


async def get_current_member(
    token: Annotated[str, Depends(token_header)],
    db: AsyncSession = Depends(get_db_session),
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"Authorization": "Bearer"},
    )
    verified_token = verify_access_token(token, credentials_exception)
    user_query = select(MemberTable).filter(
        and_(
            MemberTable.id == verified_token.user_id,
            MemberTable.phone == verified_token.phone,
        )
    )
    user_result = await db.execute(user_query)
    _user = user_result.scalars().first()
    if _user is None:
        raise credentials_exception
    user_dict = _user.__dict__
    user_dict.pop("reset_until")
    user = schemas.PydanticMember(**user_dict)
    return user
