import sqlalchemy as sa
from sqlalchemy import create_engine
from sqlalchemy.ext.automap import automap_base

from child_tracker_auth.settings import settings

meta = sa.MetaData()
meta.reflect(
    create_engine(
        str(settings.db_url).replace("aiomysql", "pymysql"), echo=settings.db_echo
    ),
    only={"members"},
)
Base = automap_base(metadata=meta)
Base.prepare()

MemberTable = Base.classes.members
