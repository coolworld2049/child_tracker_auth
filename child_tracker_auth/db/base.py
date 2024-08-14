from sqlalchemy.orm import DeclarativeBase

from child_tracker_auth.db.meta import meta


class Base(DeclarativeBase):
    """Base for all models."""

    metadata = meta
