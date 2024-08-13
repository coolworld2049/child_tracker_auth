import uuid
from typing import Optional, AsyncGenerator

from fastapi import Request, Depends
from fastapi_users import BaseUserManager, UUIDIDMixin, FastAPIUsers
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
from loguru import logger

from app.auth.backend import auth_backend
from app.email.manager import EmailManager
from app.models import User
from app.settings import settings
from app.users.database import get_user_db


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    reset_password_token_secret = settings.SECRET_KEY
    verification_token_secret = settings.SECRET_KEY

    async def on_after_register(self, user: User, request: Optional[Request] = None):
        logger.debug(f"User {user.id} has registered.")
        await self.send_registration_email(user)

    async def on_after_forgot_password(
        self, user: User, token: str, request: Optional[Request] = None
    ):
        logger.debug(
            f"User {user.id} has forgotten their password. Reset token: {token}"
        )
        await self.send_reset_password_email(user, token)

    async def on_after_request_verify(
        self, user: User, token: str, request: Optional[Request] = None
    ):
        logger.debug(
            f"Verification requested for user {user.id}. Verification token: {token}"
        )
        await self.send_verification_email(user, token)

    async def send_registration_email(self, user: User):
        subject = "Welcome to our platform!"
        body = (
            f"Hello {user.email}, welcome to our platform! Thank you for registering."
        )
        await EmailManager.send_email(user.email, subject, body)

    async def send_reset_password_email(self, user: User, token: str):
        subject = "Password Reset Request"
        reset_url = f"https://yourapp.com/reset-password?token={token}"
        body = f"Hello {user.email}, to reset your password, please visit the following link: {reset_url}"
        await EmailManager.send_email(user.email, subject, body)

    async def send_verification_email(self, user: User, token: str):
        subject = "Verify your email address"
        verify_url = f"https://yourapp.com/verify-email?token={token}"
        body = f"Hello {user.email}, please verify your email address by clicking the following link: {verify_url}"
        await EmailManager.send_email(user.email, subject, body)


async def get_user_manager(
    user_db: SQLAlchemyUserDatabase = Depends(get_user_db),
) -> AsyncGenerator:
    yield UserManager(user_db)


fastapi_users = FastAPIUsers[User, uuid.UUID](get_user_manager, [auth_backend])
current_active_user = fastapi_users.current_user(active=True)
