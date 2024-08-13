import logging

from loguru import logger
from sqlalchemy import text
from tenacity import after_log
from tenacity import before_log
from tenacity import retry
from tenacity import stop_after_attempt
from tenacity import wait_fixed

from app.db import sync_session_maker

max_tries = 60 * 2
wait_seconds = 2


@retry(
    stop=stop_after_attempt(max_tries),
    wait=wait_fixed(wait_seconds),
    before=before_log(logger, logging.INFO),
    after=after_log(logger, logging.WARN),
)
def init() -> None:
    try:
        with sync_session_maker() as db:
            db.execute(text("SELECT 1"))
    except Exception as e:
        logger.error(e)
        raise e


def prestart() -> None:
    logger.info("Initializing service")
    init()
    logger.info("Service finished initializing")
