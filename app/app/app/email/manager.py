from fastapi_mail import FastMail, MessageSchema
from loguru import logger

from app.settings import settings


class EmailManager:
    @staticmethod
    async def send_email(to_email: str, subject: str, body: str):
        message = MessageSchema(
            subject=subject, recipients=[to_email], body=body, subtype="plain"
        )

        fm = FastMail(settings.email_conf)
        await fm.send_message(message)
        logger.debug(f"Email sent to {to_email}: {subject}")
