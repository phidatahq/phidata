from typing import Optional, List
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.schema import MetaData, Table
from sqlalchemy.sql.expression import text
from sqlalchemy.engine import create_engine, Engine
from sqlalchemy.dialects import postgresql

from phi.document import Document
from phi.vectordb.base import VectorDb
from phi.utils.log import logger


class PgVector(VectorDb):
    def __init__(
        self,
        collection: str,
        dimensions: int = 1536,
        db_schema: Optional[str] = None,
        db_url: Optional[str] = None,
        db_engine: Optional[Engine] = None,
    ):
        _engine: Optional[Engine] = db_engine
        if _engine is None and db_url is not None:
            _engine = create_engine(db_url)

        if _engine is None:
            raise ValueError("Must provide either db_url or db_engine")

        # Collection attributes
        self.collection: str = collection
        self.dimensions: int = dimensions

        # Database attributes
        self.db_schema: Optional[str] = db_schema
        self.db_url: Optional[str] = db_url
        self.db_engine: Engine = _engine
        self.metadata: MetaData = MetaData(schema=self.db_schema)

        # Database session
        self._db_session: Optional[Session] = None
        self.Session: sessionmaker[Session] = sessionmaker(bind=self.db_engine)

        # Database table for the collection
        self.table: Table = self.get_table()

        logger.info("Creating extension: vector")
        with self.db_session as sess:
            sess.execute(text("create extension if not exists vector;"))
            if self.db_schema is not None:
                sess.execute(text(f"create schema if not exists {self.db_schema};"))
            sess.commit()
        logger.info("Extension created")

    @property
    def db_session(self) -> Session:
        if self._db_session is None:
            self._db_session = self.Session()
        return self._db_session

    def get_table(self) -> Table:
        from sqlalchemy.schema import Column
        from sqlalchemy.types import DateTime, String
        from pgvector.sqlalchemy import Vector

        return Table(
            self.collection,
            self.metadata,
            Column("name", String),
            Column("meta_data", postgresql.JSONB, server_default=text("'{}'::jsonb")),
            Column("content", postgresql.TEXT),
            Column("embedding", Vector(self.dimensions)),
            Column("usage", postgresql.JSONB),
            Column("created_at", DateTime(timezone=True), server_default=text("now()")),
            Column("updated_at", DateTime(timezone=True), onupdate=text("now()")),
            extend_existing=True,
        )

    def table_exists(self) -> bool:
        from sqlalchemy import inspect

        logger.info(f"Checking if table exists: {self.table.name}")
        try:
            return inspect(self.db_session.bind).has_table(self.table.name)  # type: ignore
        except Exception as e:
            logger.error(e)
            return False

    def create(self) -> None:
        if not self.table_exists():
            logger.info(f"Creating collection: {self.collection}")
            self.table.create(self.db_session.bind)  # type: ignore

    def delete(self) -> None:
        if self.table_exists():
            logger.info(f"Deleting collection: {self.collection}")
            self.table.drop(self.db_session.bind)  # type: ignore

    def insert(self, document: Document) -> None:
        stmt = postgresql.insert(self.table).values(
            name=document.name,
            meta_data=document.meta_data,
            content=document.content,
            embedding=document.embedding,
            usage=document.usage,
        )
        with self.db_session as sess:
            sess.execute(stmt)
            sess.commit()

    def search(self, query_embedding: List[float], num_documents: int = 5) -> List[Document]:
        from sqlalchemy import select

        columns = [
            self.table.c.name,
            self.table.c.meta_data,
            self.table.c.content,
            self.table.c.embedding,
            self.table.c.usage,
        ]
        # Get neighbors
        neighbors = self.db_session.scalars(
            select(*columns).order_by(self.table.c.embedding.max_inner_product(query_embedding)).limit(num_documents)
        )

        stmt = select(*columns).order_by(self.table.c.embedding.max_inner_product(query_embedding)).limit(num_documents)
        logger.info(f"Query: {stmt}")
        with self.db_session as sess:
            neighbors = sess.execute(stmt).fetchall()

        # Build relevant documents
        relevant_documents: List[Document] = []
        for neighbor in neighbors:
            relevant_documents.append(
                Document(
                    name=neighbor.name,
                    meta_data=neighbor.meta_data,
                    content=neighbor.content,
                    embedding=neighbor.embedding,
                    usage=neighbor.usage,
                )
            )

        return relevant_documents
