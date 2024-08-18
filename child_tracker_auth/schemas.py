from typing import Literal

from pydantic import BaseModel, EmailStr, ConfigDict, Field

from child_tracker_auth.db.base import MemberTable, DeviceTable, LogTable
from child_tracker_auth.utils.sa_to_pydantic import sqlalchemy_to_pydantic

PydanticMember = sqlalchemy_to_pydantic(
    MemberTable, exclude=["password_pbkdf_hash", "password", "code", "token"]
)

PydanticDevice = sqlalchemy_to_pydantic(DeviceTable)
PydanticLog = sqlalchemy_to_pydantic(LogTable)


class PydanticMemberCreate(BaseModel):
    email: EmailStr
    phone: str
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
    id: str
    phone: str


class ConfirmMailBody(BaseModel):
    email: str
    project_name: str
    url: str
    token: str


class ResponseModel(BaseModel):
    message: str


class LoginModel(BaseModel):
    phone: str


class AuthModel(BaseModel):
    phone: str
    code: int


class TokenModel(BaseModel):
    access_token: str
    token_type: str = "bearer"
