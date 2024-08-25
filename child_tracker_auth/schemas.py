import random
from datetime import datetime, timedelta
from typing import Literal

from pydantic import BaseModel, EmailStr, ConfigDict, Field, computed_field

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
PydanticLogStats = sqlalchemy_to_pydantic(
    LogTable, exclude={"device_id", "time", "wcSection_id", "wcCategory_id", "log_type"}
)

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


class Phone(BaseModel):
    name: str

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


class PhoneCall(Phone):
    name: str
    type: str
    duration: int


class PhoneBookItem(BaseModel):
    name: str
    phone: str


def generate_random_time():
    return timedelta(
        hours=random.randint(0, 23),
    ).seconds


class DeviceUsageAggregatedData(BaseModel):
    limit: int = Field(default_factory=generate_random_time)
    avg: int = Field(default_factory=generate_random_time)
    today_exp: int = Field(
        default_factory=generate_random_time,
        description="Осталось в использовании на сегодня",
    )


class DeviceUsageData(BaseModel):
    week_day: int
    hour: int
    duration: int


class DeviceUsage(BaseModel):
    name: str
    usage_data: list[DeviceUsageData]
    agg_data: DeviceUsageAggregatedData
