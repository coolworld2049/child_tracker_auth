from typing import List

from fastapi_users_db_sqlalchemy import (
    SQLAlchemyBaseOAuthAccountTableUUID,
    SQLAlchemyBaseUserTableUUID,
)
from sqlalchemy import MetaData
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Mapped, relationship, declarative_base

from app.db import sync_engine

metadata = MetaData()
metadata.reflect(sync_engine, only={"members"})

AutomapBase = automap_base(metadata=metadata)
Base = declarative_base()


class OAuthAccount(SQLAlchemyBaseOAuthAccountTableUUID, Base):
    pass


class User(SQLAlchemyBaseUserTableUUID, Base):
    oauth_accounts: Mapped[List[OAuthAccount]] = relationship(
        "OAuthAccount", lazy="joined"
    )


Base.metadata.create_all(sync_engine)
AutomapBase.prepare()
Members = AutomapBase.classes.members
