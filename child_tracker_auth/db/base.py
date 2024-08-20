import sqlalchemy as sa
from sqlalchemy import create_engine
from sqlalchemy.ext.automap import automap_base

from child_tracker_auth.settings import settings

engine = create_engine(
    str(settings.db_url).replace("aiomysql", "pymysql"), echo=settings.db_echo
)

meta = sa.MetaData()
meta.reflect(
    engine,
    only={"members", "devices", "logs", "files", "settings"},
)

Base = automap_base(metadata=meta)
Base.prepare()

MemberTable = Base.classes.members
DeviceTable = Base.classes.devices
LogTable = Base.classes.logs
FileTable = Base.classes.files
SettingsTable = Base.classes.settings
