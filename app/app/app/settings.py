import pathlib

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

env_path = pathlib.Path(__file__).parent.parent.parent.joinpath(".env")

load_dotenv(env_path)


class Settings(BaseSettings):
    HOST: str = "localhost"
    PORT: int = 8000

    DB_HOST: str
    DB_PORT: int
    DB_ROOT_USER: str
    DB_ROOT_PASSWORD: str
    DB_USERNAME: str
    DB_PASSWORD: str
    DB_DATABASE: str

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
    def db_url(self):
        return f"mysql+aiomysql://{self.DB_ROOT_USER}:{self.DB_ROOT_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_DATABASE}"


settings = Settings()
