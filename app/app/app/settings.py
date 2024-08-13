import pathlib

from dotenv import load_dotenv
from fastapi_mail import ConnectionConfig
from pydantic_settings import BaseSettings

env_path = pathlib.Path(__file__).parent.parent.parent.parent.joinpath(".env")

load_dotenv(env_path)


class Settings(BaseSettings):
    HOST: str = "localhost"
    PORT: int = 8000
    DOMAIN: str | None = None

    MARIADB_HOST: str
    MARIADB_PORT: int
    MARIADB_ROOT_USER: str
    MARIADB_ROOT_PASSWORD: str
    MARIADB_USER: str
    MARIADB_PASSWORD: str
    MARIADB_DATABASE: str

    MAIL_DRIVER: str
    MAIL_HOST: str
    MAIL_PORT: str
    MAIL_USERNAME: str
    MAIL_PASSWORD: str
    MAIL_FROM_NAME: str

    ADMIN_USERNAME: str
    ADMIN_PASSWORD: str

    SECRET_KEY: str
    CORS_ORIGINS: list[str] = ["*"]
    JWT_LIFETIME: int = 3600

    IS_DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    @property
    def async_database_url(self):
        return f"mysql+aiomysql://{self.MARIADB_ROOT_USER}:{self.MARIADB_ROOT_PASSWORD}@{self.MARIADB_HOST}:{self.MARIADB_PORT}/{self.MARIADB_DATABASE}"

    @property
    def sync_database_url(self):
        return self.async_database_url.replace("+aiomysql", "+pymysql")

    @property
    def email_conf(self):
        conf = ConnectionConfig(
            MAIL_USERNAME=self.MAIL_USERNAME,
            MAIL_PASSWORD=self.MAIL_PASSWORD,
            MAIL_FROM=self.MAIL_USERNAME,
            MAIL_FROM_NAME=self.MAIL_FROM_NAME,
            MAIL_PORT=self.MAIL_PORT,
            MAIL_SERVER=self.MAIL_HOST,
            MAIL_STARTTLS=False,
            MAIL_SSL_TLS=False,
        )
        return conf

    @property
    def https_domain(self):
        return (
            f"https://{self.DOMAIN}"
            if self.DOMAIN
            else f"https://{self.HOST}:${self.PORT}"
        )


settings = Settings()
