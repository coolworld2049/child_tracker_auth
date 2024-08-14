from typing import Literal

from pydantic import BaseModel, EmailStr, ConfigDict, Field

from db.base import MemberTable
from utils.sa_to_pydantic import sqlalchemy_to_pydantic

PydanticMember = sqlalchemy_to_pydantic(
    MemberTable, exclude=["password_pbkdf_hash", "password"]
)


class PydanticMemberCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: Literal["member", "admin", "editor", "manager"] = "member"
    active: int = Field(0, ge=0, le=1)


class RegistrationUserRepsonse(BaseModel):
    message: str
    data: PydanticMember
    model_config = ConfigDict(arbitrary_types_allowed=True)


class EmailSchema(BaseModel):
    email: EmailStr


class TokenData(BaseModel):
    id: str | None = None
