from datetime import datetime
from typing import Optional, Dict

from sqlalchemy.orm import Session, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB, TEXT
from pgvector.sqlalchemy import Vector
from sqlalchemy.types import DateTime

from phi.table.sql.base import BaseTable
from phi.utils.dttm import current_datetime_utc


class DocumentTable(BaseTable):
    """
    Table for storing Documents.

    For PG Vector, see: https://github.com/pgvector/pgvector-python#sqlalchemy
    """

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str]
    page: Mapped[Optional[int]]
    meta_data: Mapped[Optional[Dict]] = mapped_column(JSONB)
    usage: Mapped[Optional[Dict]] = mapped_column(JSONB)
    content: Mapped[str] = mapped_column(TEXT)
    embedding = mapped_column(Vector(1536))
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), default=current_datetime_utc)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), onupdate=current_datetime_utc)


def save_document_to_db(db_session: Session, document: DocumentTable) -> DocumentTable:
    """Save a document to the database"""
    db_session.add(document)
    db_session.commit()
    db_session.refresh(document)
    return document
