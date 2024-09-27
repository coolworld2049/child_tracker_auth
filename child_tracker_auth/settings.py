import enum
import pathlib
from pathlib import Path
from tempfile import gettempdir
from typing import Literal

from cashews import cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from yarl import URL

TEMP_DIR = Path(gettempdir())


class LogLevel(str, enum.Enum):
    """Possible log levels."""

    NOTSET = "NOTSET"
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    FATAL = "FATAL"


class Settings(BaseSettings):
    host: str = "127.0.0.1"
    port: int = 8000
    workers_count: int = 1
    reload: bool = False

    log_level: LogLevel = LogLevel.INFO
    environment: Literal["dev", "prod"] = "dev"

    db_host: str = "localhost"
    db_port: int = 3306
    db_user: str
    db_pass: str
    db_base: str
    db_echo: bool = False

    secret_key: str
    algorithm: str

    access_token_expire_minutes: int
    refresh_token_expire_minutes: int

    project_name: str

    sms_provider_login: str
    sms_provider_password: str
    public_dir_path: str = (
        pathlib.Path(__file__).parent.parent.joinpath("public").__str__()
    )
    mnt_public_path: str = (
        pathlib.Path(__file__).parent.parent.joinpath("mnt/public").__str__()
    )
    public_upload_media_dir_path: str = (
        pathlib.Path(__file__).parent.parent.joinpath("public/upload/media").__str__()
    )
    storage_endpoint_url: str
    storage_region: str
    storage_access_key: str
    storage_secret_key: str

    tz: str

    google_play_member_name: str = "dujEHaPLYzpnhkQDSKPe3tE7K8G6cgAN"
    google_play_member_phone: str = "+19999999999"
    google_play_member_code: int = 4985

    diskcache_directory: str = "/tmp/child_tracker_auth_cache"

    @property
    def db_url(self) -> URL:
        return URL.build(
            scheme="mysql+aiomysql",
            host=self.db_host,
            port=self.db_port,
            user=self.db_user,
            password=self.db_pass,
            path=f"/{self.db_base}",
        )

    model_config = SettingsConfigDict(
        env_file="../.env",
        env_prefix="CHILD_TRACKER_AUTH_",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

Gb = 1073741824
cache.setup(
    f"disk://?directory={settings.diskcache_directory}", size_limit=3 * Gb, shards=12
)
