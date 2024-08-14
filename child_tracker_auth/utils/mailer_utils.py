from pathlib import Path

from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from fastapi_mail.errors import ConnectionErrors
from loguru import logger

from child_tracker_auth.schemas import EmailStr
from settings import settings

config = ConnectionConfig(
    MAIL_USERNAME=settings.mail_username,
    MAIL_PASSWORD=settings.mail_password,
    MAIL_FROM=settings.mail_from,
    MAIL_PORT=settings.mail_port,
    MAIL_SERVER=settings.mail_server,
    MAIL_SSL_TLS=False,
    MAIL_STARTTLS=True,
    TEMPLATE_FOLDER=Path(__file__).parent.parent / "templates/",
)


async def send_email_async(subject: str, email_to: EmailStr, body: dict, template: str):
    message = MessageSchema(
        subject=subject,
        recipients=[
            email_to,
        ],
        template_body=body,
        subtype="html",
    )

    fm = FastMail(config)
    try:
        await fm.send_message(message, template_name=template)
        return True
    except ConnectionErrors as e:
        logger.error(e)
        return False
