import uuid
from typing import Optional

from fastapi import Depends, Request
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from fastapi_users import BaseUserManager, FastAPIUsers, UUIDIDMixin
from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    JWTStrategy,
)
from fastapi_users.db import SQLAlchemyUserDatabase
from loguru import logger

from app.db import get_user_db
from app.models import User
from app.settings import settings

conf = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_FROM=settings.MAIL_USERNAME,
    MAIL_FROM_NAME=settings.MAIL_FROM_NAME,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_HOST,
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=True
)


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    reset_password_token_secret = settings.SECRET_KEY
    verification_token_secret = settings.SECRET_KEY

    async def on_after_register(self, user: User, request: Optional[Request] = None):
        logger.debug(f"User {user.id} has registered.")
        await self.send_registration_email(user)

    async def on_after_forgot_password(
        self, user: User, token: str, request: Optional[Request] = None
    ):
        logger.debug(f"User {user.id} has forgotten their password. Reset token: {token}")
        await self.send_reset_password_email(user, token)

    async def on_after_request_verify(
        self, user: User, token: str, request: Optional[Request] = None
    ):
        logger.debug(f"Verification requested for user {user.id}. Verification token: {token}")
        await self.send_verification_email(user, token)

    async def send_registration_email(self, user: User):
        subject = "Welcome to our platform!"
        body = f"Hello {user.email}, welcome to our platform! Thank you for registering."

        await self.send_email(user.email, subject, body)

    async def send_reset_password_email(self, user: User, token: str):
        subject = "Password Reset Request"
        reset_url = f"https://yourapp.com/reset-password?token={token}"
        body = f"Hello {user.email}, to reset your password, please visit the following link: {reset_url}"

        await self.send_email(user.email, subject, body)

    async def send_verification_email(self, user: User, token: str):
        subject = "Verify your email address"
        verify_url = f"https://yourapp.com/verify-email?token={token}"
        body = f"Hello {user.email}, please verify your email address by clicking the following link: {verify_url}"

        await self.send_email(user.email, subject, body)

    @staticmethod
    async def send_email(to_email: str, subject: str, body: str):
        message = MessageSchema(
            subject=subject,
            recipients=[to_email],
            body=body,
            subtype="plain"
        )

        fm = FastMail(conf)
        await fm.send_message(message)
        logger.debug(f"Email sent to {to_email}: {subject}")


async def get_user_manager(user_db: SQLAlchemyUserDatabase = Depends(get_user_db)):
    yield UserManager(user_db)


bearer_transport = BearerTransport(tokenUrl="auth/jwt/login")


def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=settings.SECRET_KEY, lifetime_seconds=3600)


auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)

fastapi_users = FastAPIUsers[User, uuid.UUID](get_user_manager, [auth_backend])

current_active_user = fastapi_users.current_user(active=True)
