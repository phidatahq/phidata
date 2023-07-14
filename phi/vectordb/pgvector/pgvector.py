from typing import Optional, Type, List
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.engine import create_engine

from phi.document import Document
from phi.table.sql import BaseTable
from phi.vectordb.base import VectorDB
from phi.vectordb.pgvector.document_table import DocumentTable
from phi.utils.log import logger


class PGVector(VectorDB):
    def __init__(
        self,
        collection: str,
        documents_table: Type[BaseTable] = DocumentTable,
        session: Optional[Session] = None,
        connection_url: Optional[str] = None,
    ):
        _session = session
        if _session is None and connection_url is not None:
            _session = sessionmaker(bind=create_engine(connection_url))()
        if _session is None:
            raise ValueError("Must provide either connection_url or session")

        self.session: Session = _session
        self.collection = collection
        self.documents_table: Type[BaseTable] = documents_table

    def table_exists(self) -> bool:
        from sqlalchemy import inspect

        logger.info(f"Checking if table exists: {self.documents_table.__tablename__}")
        try:
            return inspect(self.session.bind).has_table(self.documents_table.__tablename__)
        except Exception as e:
            logger.error(e)
            return False

    def create(self) -> None:
        if not self.table_exists():
            logger.info(f"Creating collection: {self.collection}")
            self.documents_table.__table__.create(self.session.bind)

    def insert(self, document: Document) -> bool:
        document_row = DocumentTable(
            collection=self.collection,
            name=document.name,
            page=document.page,
            meta_data=document.meta_data,
            usage=document.usage,
            content=document.content,
            embedding=document.embedding,
        )
        saved_document = document_row.save_to_db(session=self.session)
        if saved_document is None:
            return False
        return True

    def search(self, embeddings: List[float]) -> Optional[List[Document]]:
        from sqlalchemy import select

        # Get relevant documents
        neighbors = self.session.scalars(
            select(DocumentTable).order_by(DocumentTable.embedding.max_inner_product(embeddings)).limit(5)
        )

        relevant_documents: List[Document] = []
        for neighbor in neighbors:
            relevant_documents.append(
                Document(
                    content=neighbor.content,
                    name=neighbor.name,
                    page=neighbor.page,
                    meta_data=neighbor.meta_data,
                    embedding=neighbor.embedding,
                    usage=neighbor.usage,
                )
            )

        return relevant_documents
