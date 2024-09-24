from math import sqrt
from hashlib import md5
from typing import Optional, List, Union, Dict, Any, cast

try:
    from sqlalchemy.dialects import postgresql
    from sqlalchemy.engine import create_engine, Engine
    from sqlalchemy.inspection import inspect
    from sqlalchemy.orm import Session, sessionmaker
    from sqlalchemy.schema import MetaData, Table, Column
    from sqlalchemy.sql.expression import text, func, select, desc
    from sqlalchemy.types import DateTime, String
except ImportError:
    raise ImportError("`sqlalchemy` not installed")

try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    raise ImportError("`pgvector` not installed")

from phi.document import Document
from phi.embedder import Embedder
from phi.vectordb.base import VectorDb
from phi.vectordb.distance import Distance
from phi.vectordb.pgvector.index import Ivfflat, HNSW
from phi.utils.log import logger


class PgVector(VectorDb):
    def __init__(
        self,
        table_name: str,
        schema: str = "ai",
        search_type: str = "vector",
        index: Union[Ivfflat, HNSW] = HNSW(),
        distance: Distance = Distance.cosine,
        schema_version: int = 1,
        auto_upgrade_schema: bool = False,
        db_url: Optional[str] = None,
        db_engine: Optional[Engine] = None,
        embedder: Optional[Embedder] = None,
    ):
        if not table_name:
            raise ValueError("Table name must be provided.")

        if db_engine is None and db_url is None:
            raise ValueError("Must provide either 'db_url' or 'db_engine'.")

        if db_engine is None:
            if db_url is None:
                raise ValueError("Must provide 'db_url' if 'db_engine' is not provided")
            try:
                db_engine = create_engine(db_url)
            except Exception as e:
                logger.error(f"Failed to create engine from 'db_url': {e}")
                raise

        # Collection attributes
        self.table_name: str = table_name
        self.schema: str = schema

        # Database attributes
        self.db_url: Optional[str] = db_url
        self.db_engine: Engine = db_engine
        self.metadata: MetaData = MetaData(schema=self.schema)

        # Embedder for embedding the document contents
        if embedder is None:
            from phi.embedder.openai import OpenAIEmbedder

            embedder = OpenAIEmbedder()
        self.embedder: Embedder = embedder
        self.dimensions: Optional[int] = self.embedder.dimensions

        if self.dimensions is None:
            raise ValueError("Embedder must have 'dimensions' attribute set.")

        # Distance metric
        self.distance: Distance = distance

        # Index for the table
        self.index: Union[Ivfflat, HNSW] = index

        # Search type
        self.search_type: str = search_type

        # Database session
        self.Session: sessionmaker[Session] = sessionmaker(bind=self.db_engine)

        # Database table
        self.table: Table = self.get_table()

        # Table schema version
        self.schema_version: int = schema_version
        # Automatically upgrade schema if True
        self.auto_upgrade_schema: bool = auto_upgrade_schema

        logger.debug(f"Initialized PgVector with table '{self.table_name}' in schema '{self.schema}'.")

    def get_table_v1(self) -> Table:
        if self.dimensions is None:
            raise ValueError("Embedder dimensions are not set.")
        return Table(
            self.table_name,
            self.metadata,
            Column("id", String, primary_key=True),
            Column("name", String),
            Column("meta_data", postgresql.JSONB, server_default=text("'{}'::jsonb")),
            Column("filters", postgresql.JSONB, server_default=text("'{}'::jsonb"), nullable=True),
            Column("content", postgresql.TEXT),
            Column("embedding", Vector(self.dimensions)),
            Column("usage", postgresql.JSONB),
            Column("created_at", DateTime(timezone=True), server_default=func.now()),
            Column("updated_at", DateTime(timezone=True), onupdate=func.now()),
            Column("content_hash", String),
            extend_existing=True,
        )

    def get_table(self) -> Table:
        if self.schema_version == 1:
            return self.get_table_v1()
        else:
            raise NotImplementedError(f"Unsupported schema version: {self.schema_version}")

    def table_exists(self) -> bool:
        logger.debug(f"Checking if table '{self.table.fullname}' exists.")
        try:
            return inspect(self.db_engine).has_table(self.table_name, schema=self.schema)
        except Exception as e:
            logger.error(f"Error checking if table exists: {e}")
            return False

    def create(self) -> None:
        if not self.table_exists():
            try:
                with self.db_engine.connect() as conn:
                    logger.debug("Creating extension 'vector' if not exists.")
                    conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                    if self.schema is not None:
                        logger.debug(f"Creating schema '{self.schema}' if not exists.")
                        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {self.schema};"))
                logger.debug(f"Creating table '{self.table.fullname}'.")
                self.table.create(self.db_engine, checkfirst=True)
            except Exception as e:
                logger.error(f"Error creating table '{self.table.fullname}': {e}")
                raise

    def _record_exists(self, column, value) -> bool:
        try:
            with self.Session() as sess:
                stmt = select([1]).where(column == value).limit(1)
                result = sess.execute(stmt).first()
                return result is not None
        except Exception as e:
            logger.error(f"Error checking if record exists: {e}")
            return False

    def doc_exists(self, document: Document) -> bool:
        cleaned_content = document.content.replace("\x00", "\ufffd")
        content_hash = md5(cleaned_content.encode()).hexdigest()
        return self._record_exists(self.table.c.content_hash, content_hash)

    def name_exists(self, name: str) -> bool:
        return self._record_exists(self.table.c.name, name)

    def id_exists(self, id: str) -> bool:
        return self._record_exists(self.table.c.id, id)

    def _clean_content(self, content: str) -> str:
        return content.replace("\x00", "\ufffd")

    def insert(
        self,
        documents: List[Document],
        filters: Optional[Dict[str, Any]] = None,
        batch_size: int = 100,
    ) -> None:
        records = []
        for document in documents:
            try:
                document.embed(embedder=self.embedder)
                cleaned_content = self._clean_content(document.content)
                content_hash = md5(cleaned_content.encode()).hexdigest()
                _id = document.id or content_hash
                record = {
                    "id": _id,
                    "name": document.name,
                    "meta_data": document.meta_data,
                    "filters": filters,
                    "content": cleaned_content,
                    "embedding": document.embedding,
                    "usage": document.usage,
                    "content_hash": content_hash,
                }
                records.append(record)
            except Exception as e:
                logger.error(f"Error processing document '{document.name}': {e}")
        try:
            with self.Session() as sess:
                for i in range(0, len(records), batch_size):
                    batch = records[i : i + batch_size]
                    sess.execute(self.table.insert(), batch)
                    sess.commit()
                    logger.info(f"Inserted batch of {len(batch)} documents.")
        except Exception as e:
            logger.error(f"Error inserting documents: {e}")
            sess.rollback()
            raise

    def upsert_available(self) -> bool:
        return True

    def upsert(
        self, documents: List[Document], filters: Optional[Dict[str, Any]] = None, batch_size: int = 100
    ) -> None:
        records = []
        for document in documents:
            try:
                document.embed(embedder=self.embedder)
                cleaned_content = self._clean_content(document.content)
                content_hash = md5(cleaned_content.encode()).hexdigest()
                _id = document.id or content_hash
                record = {
                    "id": _id,
                    "name": document.name,
                    "meta_data": document.meta_data,
                    "filters": filters,
                    "content": cleaned_content,
                    "embedding": document.embedding,
                    "usage": document.usage,
                    "content_hash": content_hash,
                }
                records.append(record)
            except Exception as e:
                logger.error(f"Error processing document '{document.name}': {e}")
        try:
            with self.Session() as sess:
                for i in range(0, len(records), batch_size):
                    batch = records[i : i + batch_size]
                    sess.execute(self.table.update(), batch)
                    sess.commit()
                    logger.info(f"Upserted batch of {len(batch)} documents.")
        except Exception as e:
            logger.error(f"Error upserting documents: {e}")
            sess.rollback()
            raise

    def search(self, query: str, limit: int = 5, filters: Optional[Dict[str, Any]] = None) -> List[Document]:
        if self.search_type == "vector":
            return self.vector_search(query=query, limit=limit, filters=filters)
        elif self.search_type == "fulltext":
            return self.fulltext_search(query=query, limit=limit, filters=filters)
        elif self.search_type == "hybrid":
            return self.hybrid_search(query=query, limit=limit, filters=filters)
        else:
            logger.error(f"Invalid search type '{self.search_type}'.")
            return []

    def vector_search(self, query: str, limit: int = 5, filters: Optional[Dict[str, Any]] = None) -> List[Document]:
        """
        Perform a vector similarity search using the specified distance metric.

        Args:
            query (str): The query string to search for.
            limit (int): The maximum number of results to return.
            filters (Optional[Dict[str, Any]]): Optional filters to apply.

        Returns:
            List[Document]: A list of matching Document objects.
        """
        try:
            # Get the embedding for the query string
            query_embedding = self.embedder.get_embedding(query)
            if query_embedding is None:
                logger.error(f"Error getting embedding for Query: {query}")
                return []

            # Define the columns to select
            columns = [
                self.table.c.name,
                self.table.c.meta_data,
                self.table.c.content,
                self.table.c.embedding,
                self.table.c.usage,
            ]

            # Build the base statement
            stmt = select(*columns)

            # Apply filters if provided
            if filters is not None:
                # Use the contains() method for JSONB columns to check if the filters column contains the specified filters
                stmt = stmt.where(self.table.c.filters.contains(filters))

            # Order the results based on the distance metric
            if self.distance == Distance.l2:
                stmt = stmt.order_by(self.table.c.embedding.l2_distance(query_embedding))
            elif self.distance == Distance.cosine:
                stmt = stmt.order_by(self.table.c.embedding.cosine_distance(query_embedding))
            elif self.distance == Distance.max_inner_product:
                stmt = stmt.order_by(self.table.c.embedding.max_inner_product(query_embedding))
            else:
                logger.error(f"Unknown distance metric: {self.distance}")
                return []

            # Limit the number of results
            stmt = stmt.limit(limit)
            logger.debug(f"Vector search query: {stmt}")

            # Execute the query
            try:
                with self.Session() as sess:
                    if self.index is not None:
                        if isinstance(self.index, Ivfflat):
                            sess.execute(text(f"SET LOCAL ivfflat.probes = {self.index.probes}"))
                        elif isinstance(self.index, HNSW):
                            sess.execute(text(f"SET LOCAL hnsw.ef_search = {self.index.ef_search}"))
                    neighbors = sess.execute(stmt).fetchall()
            except Exception as e:
                logger.error(f"Error searching for documents: {e}")
                logger.error("Table might not exist, creating for future use")
                self.create()
                return []

            # Build the list of Document objects
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
        except Exception as e:
            logger.error(f"Error during vector search: {e}")
            return []

    def fulltext_search(self, query: str, limit: int = 5, filters: Optional[Dict[str, Any]] = None) -> List[Document]:
        """
        Perform a full-text search on the 'content' column.

        Args:
            query (str): The search query string.
            limit (int): The maximum number of results to return.
            filters (Optional[Dict[str, Any]]): Optional filters to apply.

        Returns:
            List[Document]: A list of matching Document objects.
        """
        try:
            # Define the columns to select
            columns = [
                self.table.c.name,
                self.table.c.meta_data,
                self.table.c.content,
                self.table.c.embedding,
                self.table.c.usage,
            ]

            # Build the text search vector and query
            ts_vector = func.to_tsvector("english", self.table.c.content)
            ts_query = func.plainto_tsquery("english", query)
            rank = func.ts_rank_cd(ts_vector, ts_query)

            # Build the base statement
            stmt = select(*columns)

            # Add the full-text search condition
            stmt = stmt.where(ts_vector.op("@@")(ts_query))

            # Apply filters if provided
            if filters is not None:
                stmt = stmt.where(self.table.c.filters.contains(filters))

            # Order by the relevance rank
            stmt = stmt.order_by(rank.desc())

            # Limit the number of results
            stmt = stmt.limit(limit)

            logger.debug(f"Full-text search query: {stmt}")

            # Execute the query
            try:
                with self.Session() as sess:
                    with sess.begin():
                        results = sess.execute(stmt).fetchall()
            except Exception as e:
                logger.error(f"Error performing full-text search: {e}")
                return []

            # Build the list of Document objects
            search_results: List[Document] = []
            for result in results:
                search_results.append(
                    Document(
                        name=result.name,
                        meta_data=result.meta_data,
                        content=result.content,
                        embedder=self.embedder,
                        embedding=result.embedding,
                        usage=result.usage,
                    )
                )

            return search_results
        except Exception as e:
            logger.error(f"Error during full-text search: {e}")
            return []

    def hybrid_search(self, query: str, limit: int = 5, filters: Optional[Dict[str, Any]] = None) -> List[Document]:
        """
        Perform a hybrid search combining vector similarity and full-text search.

        Args:
            query (str): The query string to search for.
            limit (int): The maximum number of results to return.
            filters (Optional[Dict[str, Any]]): Optional filters to apply.

        Returns:
            List[Document]: A list of matching Document objects.
        """
        try:
            # Get the embedding for the query string
            query_embedding = self.embedder.get_embedding(query)
            if query_embedding is None:
                logger.error(f"Error getting embedding for Query: {query}")
                return []

            # Define the columns to select
            columns = [
                self.table.c.name,
                self.table.c.meta_data,
                self.table.c.content,
                self.table.c.embedding,
                self.table.c.usage,
            ]

            # Build the text search vector and query
            ts_vector = func.to_tsvector("english", self.table.c.content)
            ts_query = func.plainto_tsquery("english", query)
            text_rank = func.ts_rank_cd(ts_vector, ts_query)

            # Compute the vector similarity score
            if self.distance == Distance.l2:
                # For L2 distance, smaller distances are better
                vector_distance = self.table.c.embedding.l2_distance(query_embedding)
                # Invert and normalize the distance to get a similarity score between 0 and 1
                vector_score = 1 / (1 + vector_distance)
            elif self.distance == Distance.cosine:
                # For cosine distance, smaller distances are better
                vector_distance = self.table.c.embedding.cosine_distance(query_embedding)
                vector_score = 1 / (1 + vector_distance)
            elif self.distance == Distance.max_inner_product:
                # For inner product, higher values are better
                # Assume embeddings are normalized, so inner product ranges from -1 to 1
                raw_vector_score = self.table.c.embedding.max_inner_product(query_embedding)
                # Normalize to range [0, 1]
                vector_score = (raw_vector_score + 1) / 2
            else:
                logger.error(f"Unknown distance metric: {self.distance}")
                return []

            # Apply weights to control the influence of each score
            vector_score_weight = 0.5  # weight for vector score
            text_rank_weight = 1 - vector_score_weight  # weight for text rank

            # Combine the scores into a hybrid score
            hybrid_score = (vector_score_weight * vector_score) + (text_rank_weight * text_rank)

            # Build the base statement, including the hybrid score
            stmt = select(*columns, hybrid_score.label("hybrid_score"))

            # Add the full-text search condition
            stmt = stmt.where(ts_vector.op("@@")(ts_query))

            # Apply filters if provided
            if filters is not None:
                stmt = stmt.where(self.table.c.filters.contains(filters))

            # Order the results by the hybrid score in descending order
            stmt = stmt.order_by(desc("hybrid_score"))

            # Limit the number of results
            stmt = stmt.limit(limit)
            logger.debug(f"Hybrid search query: {stmt}")

            # Execute the query
            try:
                with self.Session() as sess:
                    if self.index is not None:
                        if isinstance(self.index, Ivfflat):
                            sess.execute(text(f"SET LOCAL ivfflat.probes = {self.index.probes}"))
                        elif isinstance(self.index, HNSW):
                            sess.execute(text(f"SET LOCAL hnsw.ef_search = {self.index.ef_search}"))
                    results = sess.execute(stmt).fetchall()
            except Exception as e:
                logger.error(f"Error performing hybrid search: {e}")
                return []

            # Build the list of Document objects
            search_results: List[Document] = []
            for result in results:
                search_results.append(
                    Document(
                        name=result.name,
                        meta_data=result.meta_data,
                        content=result.content,
                        embedder=self.embedder,
                        embedding=result.embedding,
                        usage=result.usage,
                    )
                )

            return search_results
        except Exception as e:
            logger.error(f"Error during hybrid search: {e}")
            return []

    def delete(self) -> None:
        if self.table_exists():
            try:
                logger.debug(f"Dropping table '{self.table.fullname}'.")
                self.table.drop(self.db_engine)
                logger.info(f"Table '{self.table.fullname}' dropped successfully.")
            except Exception as e:
                logger.error(f"Error dropping table '{self.table.fullname}': {e}")
                raise
        else:
            logger.info(f"Table '{self.table.fullname}' does not exist.")

    def exists(self) -> bool:
        return self.table_exists()

    def get_count(self) -> int:
        try:
            with self.Session() as sess:
                with sess.begin():
                    stmt = select(func.count(self.table.c.name)).select_from(self.table)
                    result = sess.execute(stmt).scalar()
                    return int(result) if result is not None else 0
        except Exception as e:
            logger.error(f"Error getting count from table '{self.table.fullname}': {e}")
            return 0

    def optimize(self, force_recreate: bool = False) -> None:
        """
        Optimize the vector database by creating or recreating necessary indexes.

        Parameters:
        - force_recreate (bool): If True, existing indexes will be dropped and recreated.

        Returns:
        - None
        """
        logger.debug("==== Optimizing Vector DB ====")
        self._create_vector_index(force_recreate=force_recreate)
        self._create_gin_index(force_recreate=force_recreate)
        logger.debug("==== Optimized Vector DB ====")

    def _index_exists(self, index_name: str) -> bool:
        inspector = inspect(self.db_engine)
        indexes = inspector.get_indexes(self.table.name, schema=self.schema)
        return any(idx["name"] == index_name for idx in indexes)

    def _drop_index(self, index_name: str) -> None:
        try:
            with self.Session() as sess:
                with sess.begin():
                    drop_index_sql = f'DROP INDEX IF EXISTS "{self.schema}"."{index_name}";'
                    sess.execute(text(drop_index_sql))
        except Exception as e:
            logger.error(f"Error dropping index '{index_name}': {e}")
            raise

    def _create_vector_index(self, force_recreate: bool = False) -> None:
        if self.index is None:
            logger.debug("No vector index specified, skipping vector index optimization.")
            return

        # Generate index name if not provided
        if self.index.name is None:
            index_type = "ivfflat" if isinstance(self.index, Ivfflat) else "hnsw"
            self.index.name = f"{self.table_name}_{index_type}_index"

        # Determine index distance operator
        index_distance = {
            Distance.l2: "vector_l2_ops",
            Distance.max_inner_product: "vector_ip_ops",
            Distance.cosine: "vector_cosine_ops",
        }.get(self.distance, "vector_cosine_ops")

        # Get the fully qualified table name
        table_fullname = self.table.fullname  # includes schema if any

        # Check if vector index already exists
        vector_index_exists = self._index_exists(self.index.name)

        if vector_index_exists:
            logger.info(f"Vector index '{self.index.name}' already exists.")
            if force_recreate:
                logger.info(f"Force recreating vector index '{self.index.name}'. Dropping existing index.")
                self._drop_index(self.index.name)
            else:
                logger.info(f"Skipping vector index creation as index '{self.index.name}' already exists.")
                return

        # Proceed to create the vector index
        try:
            with self.Session() as sess:
                with sess.begin():
                    # Set configuration parameters
                    if self.index.configuration:
                        logger.debug(f"Setting configuration: {self.index.configuration}")
                        for key, value in self.index.configuration.items():
                            sess.execute(text(f"SET {key} = :value;"), {"value": value})

                    if isinstance(self.index, Ivfflat):
                        self._create_ivfflat_index(sess, table_fullname, index_distance)
                    elif isinstance(self.index, HNSW):
                        self._create_hnsw_index(sess, table_fullname, index_distance)
                    else:
                        logger.error(f"Unknown index type: {type(self.index)}")
                        return
        except Exception as e:
            logger.error(f"Error creating vector index '{self.index.name}': {e}")
            raise

    def _create_ivfflat_index(self, sess: Session, table_fullname: str, index_distance: str) -> None:
        # Cast index to Ivfflat for type hinting
        self.index = cast(Ivfflat, self.index)

        # Determine number of lists
        num_lists = self.index.lists
        if self.index.dynamic_lists:
            total_records = self.get_count()
            logger.debug(f"Number of records: {total_records}")
            if total_records < 1000000:
                num_lists = max(int(total_records / 1000), 1)  # Ensure at least one list
            else:
                num_lists = max(int(sqrt(total_records)), 1)

        # Set ivfflat.probes
        sess.execute(text("SET ivfflat.probes = :probes;"), {"probes": self.index.probes})

        logger.debug(
            f"Creating Ivfflat index '{self.index.name}' on table '{table_fullname}' with "
            f"lists: {num_lists}, probes: {self.index.probes}, "
            f"and distance metric: {index_distance}"
        )

        # Create index
        create_index_sql = text(
            f'CREATE INDEX "{self.index.name}" ON {table_fullname} '
            f"USING ivfflat (embedding {index_distance}) "
            f"WITH (lists = :num_lists);"
        )
        sess.execute(create_index_sql, {"num_lists": num_lists})

    def _create_hnsw_index(self, sess: Session, table_fullname: str, index_distance: str) -> None:
        # Cast index to HNSW for type hinting
        self.index = cast(HNSW, self.index)

        logger.debug(
            f"Creating HNSW index '{self.index.name}' on table '{table_fullname}' with "
            f"m: {self.index.m}, ef_construction: {self.index.ef_construction}, "
            f"and distance metric: {index_distance}"
        )

        # Create index
        create_index_sql = text(
            f'CREATE INDEX "{self.index.name}" ON {table_fullname} '
            f"USING hnsw (embedding {index_distance}) "
            f"WITH (m = :m, ef_construction = :ef_construction);"
        )
        sess.execute(create_index_sql, {"m": self.index.m, "ef_construction": self.index.ef_construction})

    def _create_gin_index(self, force_recreate: bool = False) -> None:
        gin_index_name = f"{self.table_name}_content_gin_index"

        gin_index_exists = self._index_exists(gin_index_name)

        if gin_index_exists:
            logger.info(f"GIN index '{gin_index_name}' already exists.")
            if force_recreate:
                logger.info(f"Force recreating GIN index '{gin_index_name}'. Dropping existing index.")
                self._drop_index(gin_index_name)
            else:
                logger.info(f"Skipping GIN index creation as index '{gin_index_name}' already exists.")
                return

        # Proceed to create GIN index
        try:
            with self.Session() as sess:
                with sess.begin():
                    logger.debug(f"Creating GIN index '{gin_index_name}' on table '{self.table.fullname}'.")
                    # Create index
                    create_gin_index_sql = text(
                        f'CREATE INDEX "{gin_index_name}" ON {self.table.fullname} '
                        f"USING gin (to_tsvector('english', content));"
                    )
                    sess.execute(create_gin_index_sql)
        except Exception as e:
            logger.error(f"Error creating GIN index '{gin_index_name}': {e}")
            raise

    def clear(self) -> bool:
        from sqlalchemy import delete

        try:
            with self.Session() as sess:
                sess.execute(delete(self.table))
                sess.commit()
                logger.info(f"Cleared all records from table '{self.table.fullname}'.")
                return True
        except Exception as e:
            logger.error(f"Error clearing table '{self.table.fullname}': {e}")
            sess.rollback()
            return False
