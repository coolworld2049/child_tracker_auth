import enum
import random
import typing
from datetime import datetime, timedelta
from io import BytesIO
from typing import Literal

import numpy as np
from loguru import logger
from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from child_tracker_auth.db.base import (
    MemberTable,
    DeviceTable,
    LogTable,
    FileTable,
    SettingsTable,
    engine,
    MediaTable,
    MemberAccountsTable,
)
from child_tracker_auth.db.enums import get_enum_values
from child_tracker_auth.utils.sa_to_pydantic import sqlalchemy_to_pydantic

PydanticMember = sqlalchemy_to_pydantic(
    MemberTable, exclude=["password_pbkdf_hash", "password", "code", "token"]
)
PydanticMemberAccount = sqlalchemy_to_pydantic(MemberAccountsTable)

PydanticDevice = sqlalchemy_to_pydantic(DeviceTable)
PydanticLog = sqlalchemy_to_pydantic(LogTable)

PydanticFile = sqlalchemy_to_pydantic(FileTable)
PydanticMedia = sqlalchemy_to_pydantic(MediaTable)
PydanticSettings = sqlalchemy_to_pydantic(SettingsTable)

log_type_values = get_enum_values(
    engine=engine, table_name="logs", column_name="log_type"
)

LogTypeEnum = enum.Enum("LogTypeEnum", [(x, x) for x in log_type_values])

sms_type_values = list(filter(lambda c: "sms" in c, log_type_values))
LogMessageEnum = enum.Enum(
    "LogMessageEnum", [*[(x, x) for x in sms_type_values], ("all", "all")]
)


class DataType(enum.Enum):
    string = str
    number = int
    boolean = bool


def convert_value_type(value: str) -> np.ndarray:
    try:
        if value == "":
            return value
        f = BytesIO("\n".join([value]).encode())
        arr = np.genfromtxt(f, dtype=None, encoding="utf-8", delimiter="\n")
        return arr
    except Exception as e:
        logger.error(
            (
                value,
                e,
            )
        )
        return None


class PydanticSettingsWithTypeBase(BaseModel):
    @computed_field
    @property
    def typed_value(self) -> typing.Any:
        v = convert_value_type(self.value)
        if v is None:
            return self.value
        elif v == "":
            return self.value
        return v.item()


class PydanticSettingsWithTypeKey(BaseModel):
    key: str
    data_type: str | None = None


class PydanticSettingsWithType(PydanticSettings, PydanticSettingsWithTypeBase):
    pass


class PydanticDeviceUpdate(BaseModel):
    name: str


class ResponseModel(BaseModel):
    message: str


class PydanticMemberCreate(BaseModel):
    phone: str
    name: str
    role: Literal["member", "admin", "editor", "manager"] = "member"
    active: int = Field(0, ge=0, le=1)
    region: str | None = None

    @field_validator("phone")
    def phone_v(cls, v):
        if not str(v).startswith("+"):
            raise ValueError(f"The phone number must start with '+'")
        return v


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
        d = ","
        spl = self.name.split(d)
        if len(spl) < 1:
            if not spl[0].replace("+", "").isnumeric():
                return None
            return self.name
        return spl[0].strip()

    @computed_field
    @property
    def sub(self) -> str:
        d = ","
        spl = self.name.split(d)
        if len(spl) < 2:
            return None
        return spl[1].strip()


class PhoneCall(Phone):
    name: str
    type: str
    duration: int

    @computed_field
    @property
    def status(self) -> Literal["success", "fail"]:
        return "success" if self.duration > 0 else "fail"


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
    duration: str


class DeviceUsage(BaseModel):
    name: str
    usage_data: list[DeviceUsageData]
    agg_data: DeviceUsageAggregatedData


class DeviceMessage(BaseModel):
    avatar: str
    name: str
    text: str
    time: str
    message_type: str


class DeviceInternetActivitySite(BaseModel):
    visit_count: int
    duration: int


class DeviceInternetActivityAggData(BaseModel):
    total_sites_count: int
    total_sites_visit: int
    total_duration: int


class DeviceInternetActivity(BaseModel):
    usage_data: dict[str, DeviceInternetActivitySite]
    agg_data: DeviceInternetActivityAggData


class ResonseModel(BaseModel):
    data: list[typing.Any] = []


class Conversation(BaseModel):
    phone_info: Phone
    messages: dict[str, list[DeviceMessage]]


class PydanticFileRespone(PydanticFile):
    url: str


class PydanticMediaRespone(PydanticMedia):
    url: str


class MemberAccount(PydanticMemberAccount):
    pass
