from datetime import datetime
from typing import Literal

from pydantic import (BaseModel, EmailStr, ConfigDict, Field, computed_field)

from child_tracker_auth.db.base import (
    MemberTable,
    DeviceTable,
    LogTable,
    FileTable,
    SettingsTable,
    engine,
)
from child_tracker_auth.db.enums import get_enum_values
from child_tracker_auth.utils.sa_to_pydantic import sqlalchemy_to_pydantic

PydanticMember = sqlalchemy_to_pydantic(
    MemberTable, exclude=["password_pbkdf_hash", "password", "code", "token"]
)
PydanticDevice = sqlalchemy_to_pydantic(DeviceTable)
PydanticLog = sqlalchemy_to_pydantic(LogTable)
PydanticFile = sqlalchemy_to_pydantic(FileTable)
PydanticSettings = sqlalchemy_to_pydantic(SettingsTable)

log_type_values = get_enum_values(
    engine=engine, table_name="logs", column_name="log_type"
)


class ResponseModel(BaseModel):
    message: str


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


class LoginModel(BaseModel):
    phone: str


class AuthModel(BaseModel):
    phone: str
    code: int


class TokenData(BaseModel):
    user_id: int
    phone: str
    exp: datetime | None = None


class RefreshTokenModel(BaseModel):
    refresh_token: str


class TokenModel(RefreshTokenModel):
    access_token: str
    token_type: str = "bearer"


class PhoneCall(BaseModel):
    name: str
    type: str
    duration: int

    @computed_field
    @property
    def phone(self) -> str:
        spl = self.name.split(" ")
        if len(spl) < 1:
            return self.name
        return spl[0]

    @computed_field
    @property
    def sub(self) -> str:
        spl = self.name.split(" ")
        if len(spl) < 2:
            return None
        return spl[1]
