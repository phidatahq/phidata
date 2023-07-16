from datetime import datetime
from typing import Optional, Dict

from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column
from sqlalchemy.dialects.postgresql import JSONB, TEXT
from sqlalchemy.types import DateTime, BigInteger
from sqlalchemy.sql.expression import text
from pgvector.sqlalchemy import Vector

from phi.utils.dttm import current_datetime_utc


class PgVectorTable(DeclarativeBase):
    """
    Base class for PGVector collections.
    This class defines a series of common elements that are used in all collections.

    For PG Vector, see: https://github.com/pgvector/pgvector-python#sqlalchemy
    For SQLAlchemy, see:
        - https://docs.sqlalchemy.org/en/20/orm/mapping_api.html#sqlalchemy.orm.DeclarativeBase
        - https://docs.sqlalchemy.org/en/20/orm/declarative_mixins.html#augmenting-the-base
    """

    @declared_attr.directive
    def __tablename__(cls) -> str:
        return cls.__name__.lower()

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str]
    meta_data: Mapped[Dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    content: Mapped[str] = mapped_column(TEXT)
    embedding = mapped_column(Vector(1536))
    usage: Mapped[Optional[Dict]] = mapped_column(JSONB)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), default=current_datetime_utc)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), onupdate=current_datetime_utc)
