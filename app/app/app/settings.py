import pathlib

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

env_path = pathlib.Path(__file__).parent.parent.parent.parent.joinpath(".env")

load_dotenv(env_path)


class Settings(BaseSettings):
    HOST: str = "localhost"
    PORT: int = 8000

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
    IS_DEBUG: bool = False

    @property
    def async_database_url(self):
        return f"mysql+aiomysql://{self.MARIADB_ROOT_USER}:{self.MARIADB_ROOT_PASSWORD}@{self.MARIADB_HOST}:{self.MARIADB_PORT}/{self.MARIADB_DATABASE}"

    @property
    def sync_database_url(self):
        return self.async_database_url.replace("+aiomysql", "+pymysql")


settings = Settings()
