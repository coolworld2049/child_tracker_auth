from functools import lru_cache

from sqlalchemy import text, Engine

from child_tracker_auth.settings import settings


@lru_cache
def get_enum_values(engine: Engine, table_name: str, column_name: str):
    with engine.connect() as conn:
        q = f"""SELECT SUBSTRING(COLUMN_TYPE,5)
                FROM information_schema.COLUMNS WHERE
                TABLE_SCHEMA='{settings.db_base}'
                AND TABLE_NAME='{table_name}'
                AND COLUMN_NAME='{column_name}'
                """
        rq = conn.execute(text(q))
        r = rq.scalars().first()
        r_processed = [
            x.replace("'", "")
            for x in str(r).replace("(", "").replace(")", "").split(",")
        ]
        return r_processed
