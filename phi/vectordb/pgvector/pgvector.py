import copy
from typing import List, Optional, Type
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.engine import create_engine

from phi.document import Document
from phi.table.sql import BaseTable
from phi.vectordb.base import VectorDB
from phi.vectordb.pgvector.document_table import DocumentTable


class PGVector(VectorDB):
    def __init__(
        self,
        collection_name: str,
        table_format: Type[BaseTable] = DocumentTable,
        connection_url: Optional[str] = None,
        session: Optional[Session] = None,
    ):
        if connection_url is None and session is None:
            raise ValueError("Must provide either connection_url or session")
        if connection_url is not None and session is not None:
            raise ValueError("Must provide either connection_url or session, not both")

        self.session: Session

        if session is not None:
            self.session = session
        elif connection_url is not None:
            self.session = sessionmaker(bind=create_engine(connection_url))()

        self.collection_name = collection_name
        self.db_table: Type[BaseTable] = copy.deepcopy(table_format)
        self.db_table.__tablename__ = collection_name

    def create(self) -> None:
        pass

    def upsert(self, documents: List[Document]) -> None:
        pass
