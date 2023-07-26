from typing import Optional, List

try:
    from sqlalchemy.dialects import postgresql
    from sqlalchemy.engine import create_engine, Engine
    from sqlalchemy.inspection import inspect
    from sqlalchemy.orm import Session, sessionmaker
    from sqlalchemy.schema import MetaData, Table, Column
    from sqlalchemy.sql.expression import text
    from sqlalchemy.types import DateTime, String
except ImportError:
    raise ImportError("`sqlalchemy` not installed")

try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    raise ImportError("`pgvector` not installed")

from phi.document import Document
from phi.embedder import Embedder
from phi.embedder.openai import OpenAIEmbedder
from phi.vectordb.base import VectorDb
from phi.utils.log import logger


class PgVector(VectorDb):
    def __init__(
        self,
        collection: str,
        schema: Optional[str] = None,
        db_url: Optional[str] = None,
        db_engine: Optional[Engine] = None,
        embedder: Optional[Embedder] = None,
    ):
        _engine: Optional[Engine] = db_engine
        if _engine is None and db_url is not None:
            _engine = create_engine(db_url)

        if _engine is None:
            raise ValueError("Must provide either db_url or db_engine")

        # Collection attributes
        self.collection: str = collection

        # Database attributes
        self.schema: Optional[str] = schema
        self.db_url: Optional[str] = db_url
        self.db_engine: Engine = _engine
        self.metadata: MetaData = MetaData(schema=self.schema)

        # Embedder for embedding the document contents
        self.embedder: Embedder = embedder or OpenAIEmbedder()
        self.dimensions: int = self.embedder.dimensions

        # Database session
        self.Session: sessionmaker[Session] = sessionmaker(bind=self.db_engine)

        # Database table for the collection
        self.table: Table = self.get_table()

    def get_table(self) -> Table:
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
        logger.debug(f"Checking if table exists: {self.table.name}")
        try:
            return inspect(self.db_engine).has_table(self.table.name, schema=self.schema)
        except Exception as e:
            logger.error(e)
            return False

    def create(self) -> None:
        if not self.table_exists():
            with self.Session() as sess:
                with sess.begin():
                    logger.debug("Creating extension: vector")
                    sess.execute(text("create extension if not exists vector;"))
                    if self.schema is not None:
                        sess.execute(text(f"create schema if not exists {self.schema};"))
            logger.debug(f"Creating table: {self.collection}")
            self.table.create(self.db_engine)

    def insert(self, documents: List[Document]) -> None:
        with self.Session() as sess:
            with sess.begin():
                for document in documents:
                    document.embed(embedder=self.embedder)
                    stmt = postgresql.insert(self.table).values(
                        name=document.name,
                        meta_data=document.meta_data,
                        content=document.content,
                        embedding=document.embedding,
                        usage=document.usage,
                    )
                    sess.execute(stmt)
                    logger.debug(f"Inserted document: {document.name} ({document.meta_data})")

    def upsert(self, documents: List[Document]) -> None:
        """
        Upsert documents into the database.

        Args:
            documents (List[Document]): List of documents to upsert

        TODO: This is not working as expected. Need to fix.
        """
        with self.Session() as sess:
            with sess.begin():
                for document in documents:
                    document.embed(embedder=self.embedder)
                    stmt = postgresql.insert(self.table).values(
                        name=document.name,
                        meta_data=document.meta_data,
                        content=document.content,
                        embedding=document.embedding,
                        usage=document.usage,
                    )
                    stmt = stmt.on_conflict_do_update(
                        index_elements=["name", "meta_data"],
                        set_=dict(
                            content=stmt.excluded.content,
                            embedding=stmt.excluded.embedding,
                            usage=stmt.excluded.usage,
                        ),
                    )
                    sess.execute(stmt)
                    logger.debug(f"Upserted document: {document.name} ({document.meta_data})")

    def search(self, query: str, relevant_documents: int = 5) -> List[Document]:
        from sqlalchemy.sql.expression import select

        query_embedding = self.embedder.get_embedding(query)
        if query_embedding is None:
            logger.error(f"Error getting embedding for Query: {query}")
            return []

        columns = [
            self.table.c.name,
            self.table.c.meta_data,
            self.table.c.content,
            self.table.c.embedding,
            self.table.c.usage,
        ]

        stmt = (
            select(*columns)
            .order_by(self.table.c.embedding.max_inner_product(query_embedding))
            .limit(relevant_documents)
        )
        logger.debug(f"Query: {stmt}")

        # Get neighbors
        with self.Session() as sess:
            with sess.begin():
                neighbors = sess.execute(stmt).fetchall() or []

        # Build search results
        search_results: List[Document] = []
        for neighbor in neighbors:
            search_results.append(
                Document(
                    name=neighbor.name,
                    meta_data=neighbor.meta_data,
                    content=neighbor.content,
                    embedder=self.embedder,
                    embedding=neighbor.embedding,
                    usage=neighbor.usage,
                )
            )

        return search_results

    def delete(self) -> None:
        if self.table_exists():
            logger.debug(f"Deleting table: {self.collection}")
            self.table.drop(self.db_engine)

    def exists(self) -> bool:
        return self.table_exists()
