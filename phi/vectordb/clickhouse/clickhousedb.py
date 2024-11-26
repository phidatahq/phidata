from hashlib import md5
from typing import Any, Dict, List, Optional

from phi.vectordb.clickhouse.index import HNSW

try:
    import clickhouse_connect
    import clickhouse_connect.driver.client
except ImportError:
    raise ImportError(
        "`clickhouse-connect` not installed. "
        "Use `pip install 'clickhouse-connect'` to install it"
    )

from phi.document import Document
from phi.embedder import Embedder
from phi.utils.log import logger
from phi.vectordb.base import VectorDb
from phi.vectordb.distance import Distance


class ClickhouseDb(VectorDb):
    def __init__(
        self,
        table_name: str,
        host: str,
        username: Optional[str] = None,
        password: str = "",
        port: int = 0,
        database_name: str = "ai",
        dsn: Optional[str] = None,
        compress: str = "lz4",
        client: Optional[clickhouse_connect.driver.client.Client] = None,
        embedder: Optional[Embedder] = None,
        distance: Distance = Distance.cosine,
        index: Optional[HNSW] = HNSW(),
    ):
        if not client:
            client = clickhouse_connect.get_client(
                host=host,
                username=username,  # type: ignore
                password=password,
                database=database_name,
                port=port,
                dsn=dsn,
                compress=compress,
            )

        # Database attributes
        self.client = client
        self.database_name = database_name
        self.table_name = table_name

        # Embedder for embedding the document contents
        _embedder = embedder
        if _embedder is None:
            from phi.embedder.openai import OpenAIEmbedder

            _embedder = OpenAIEmbedder()
        self.embedder: Embedder = _embedder
        self.dimensions: Optional[int] = self.embedder.dimensions

        # Distance metric
        self.distance: Distance = distance

        # Index for the collection
        self.index: Optional[HNSW] = index

    def _get_base_parameters(self) -> Dict[str, Any]:
        return {
            "table_name": self.table_name,
            "database_name": self.database_name,
        }

    def table_exists(self) -> bool:
        logger.debug(f"Checking if table exists: {self.table_name}")
        try:
            parameters = self._get_base_parameters()
            return bool(
                self.client.command(
                    "EXISTS TABLE %(database_name).%(table_name)s",
                    parameters=parameters,
                )
            )
        except Exception as e:
            logger.error(e)
            return False

    def create(self) -> None:
        if not self.table_exists():
            logger.debug(f"Creating Database: {self.database_name}")
            parameters = {"database_name": self.database_name}
            self.client.command(
                f"CREATE DATABASE IF NOT EXISTS %(database_name)s",
                parameters=parameters,
            )

            logger.debug(f"Creating table: {self.table_name}")
            
            parameters = self._get_base_parameters()
            
            if isinstance(self.index, HNSW):
                index = f"INDEX idx vectors TYPE vector_similarity('hnsw', L2Distance, {self.index.}) "
            
            self.client.command(
                """CREATE TABLE IF NOT EXISTS %(database_name).%(table_name)s 
                (
                    id String,
                    name String,
                    meta_data JSON DEFAULT '{}',
                    content String,
                    embedding Array(Float32),
                    usage JSON,
                    created_at DateTime('UTC') DEFAULT now(),
                    content_hash String,
                    PRIMARY KEY (id)
                    INDEX idx vectors TYPE vector_similarity('hnsw', 'L2Distance') 
                ) ENGINE = ReplacingMergeTree ORDER BY id""",
                parameters=parameters,
            )

    def doc_exists(self, document: Document) -> bool:
        """
        Validating if the document exists or not

        Args:
            document (Document): Document to validate
        """
        cleaned_content = document.content.replace("\x00", "\ufffd")
        parameters = self._get_base_parameters()
        parameters["content_hash"] = md5(cleaned_content.encode()).hexdigest()

        result = self.client.query(
            "SELECT content_hash FROM %(database_name).%(table_name)s WHERE content_hash = %(content_hash)s",
            parameters=parameters,
        )
        return bool(result)

    def name_exists(self, name: str) -> bool:
        """
        Validate if a row with this name exists or not

        Args:
            name (str): Name to check
        """
        parameters = self._get_base_parameters()
        parameters["name"] = name

        result = self.client.query(
            "SELECT name FROM %(database_name).%(table_name)s WHERE name = %(name)s",
            parameters=parameters,
        )
        return bool(result)

    def id_exists(self, id: str) -> bool:
        """
        Validate if a row with this id exists or not

        Args:
            id (str): Id to check
        """
        parameters = self._get_base_parameters()
        parameters["id"] = id

        result = self.client.query(
            "SELECT id FROM %(database_name).%(table_name)s WHERE id = %(id)s",
            parameters=parameters,
        )
        return bool(result)

    def insert(
        self,
        documents: List[Document],
        filters: Optional[Dict[str, Any]] = None,
    ) -> None:
        rows: List[List[Any]] = []
        for document in documents:
            document.embed(embedder=self.embedder)
            cleaned_content = document.content.replace("\x00", "\ufffd")
            content_hash = md5(cleaned_content.encode()).hexdigest()
            _id = document.id or content_hash

            row: List[Any] = [
                _id,
                document.name,
                document.meta_data,
                cleaned_content,
                document.embedding,
                document.usage,
                content_hash,
            ]
            rows.append(row)

        self.client.insert(
            f"{self.database_name}.{self.table_name}",
            rows,
            column_names=[
                "id",
                "name",
                "meta_data",
                "content",
                "embedding",
                "usage",
                "content_hash",
            ],
        )
        logger.debug(f"Inserted {len(documents)} documents")

    def upsert_available(self) -> bool:
        return True

    def upsert(
        self,
        documents: List[Document],
        filters: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Upsert documents into the database.

        Args:
            documents (List[Document]): List of documents to upsert
            filters (Optional[Dict[str, Any]]): Filters to apply while upserting documents
            batch_size (int): Batch size for upserting documents
        """
        # We are using ReplacingMergeTree engine in our table, so we need to insert the documents,
        # then call SELECT with FINAL
        self.insert(documents=documents, filters=filters)

        parameters = self._get_base_parameters()
        self.client.query(
            "SELECT id FROM %(database_name).%(table_name)s FINAL",
            parameters=parameters,
        )

    def search(
        self, query: str, limit: int = 5, filters: Optional[Dict[str, Any]] = None
    ) -> List[Document]:
        query_embedding = self.embedder.get_embedding(query)
        if query_embedding is None:
            logger.error(f"Error getting embedding for Query: {query}")
            return []

        parameters = self._get_base_parameters()
        where_query = ""
        if filters:
            query_filters: List[str] = []
            for key, value in filters.values():
                query_filters.append(f"%({key}_key)s = %({key}_value)")
                parameters[f"{key}_key"] = key
                parameters[f"{key}_value"] = value
            where_query = f"WHERE {' AND '.join(query_filters)}"

        order_by_query = ""
        if self.distance == Distance.l2:
            order_by_query = "ORDER BY L2Distance(embedding, %(query_embedding)s)"
            parameters["query_embedding"] = query_embedding
        if self.distance == Distance.cosine:
            order_by_query = "ORDER BY cosineDistance(embedding, %(query_embedding)s)"
            parameters["query_embedding"] = query_embedding

        clickhouse_query = (
            "SELECT name, meta_data, content, embedding, usage FROM %(database_name).%(table_name)s "
            f"{where_query} {order_by_query} LIMIT {limit}"
        )
        logger.debug(f"Query: {clickhouse_query}")
        logger.debug(f"Params: {parameters}")

        result = self.client.query(
            clickhouse_query,
            parameters=parameters,
        )

        # Get neighbors
        try:
            with self.Session() as sess:
                with sess.begin():
                    if self.index is not None:
                        if isinstance(self.index, Ivfflat):
                            sess.execute(
                                text(f"SET LOCAL ivfflat.probes = {self.index.probes}")
                            )
                        elif isinstance(self.index, HNSW):
                            sess.execute(
                                text(
                                    f"SET LOCAL hnsw.ef_search  = {self.index.ef_search}"
                                )
                            )
                    neighbors = sess.execute(stmt).fetchall() or []
        except Exception as e:
            logger.error(f"Error searching for documents: {e}")
            logger.error("Table might not exist, creating for future use")
            self.create()
            return []

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

    def drop(self) -> None:
        if self.table_exists():
            logger.debug(f"Deleting table: {self.collection}")
            self.table.drop(self.db_engine)

    def exists(self) -> bool:
        return self.table_exists()

    def get_count(self) -> int:
        with self.Session() as sess:
            with sess.begin():
                stmt = select(func.count(self.table.c.name)).select_from(self.table)
                result = sess.execute(stmt).scalar()
                if result is not None:
                    return int(result)
                return 0

    def optimize(self) -> None:
        from math import sqrt

        logger.debug("==== Optimizing Vector DB ====")
        if self.index is None:
            return

        if self.index.name is None:
            _type = "ivfflat" if isinstance(self.index, Ivfflat) else "hnsw"
            self.index.name = f"{self.collection}_{_type}_index"

        index_distance = "vector_cosine_ops"
        if self.distance == Distance.l2:
            index_distance = "vector_l2_ops"
        if self.distance == Distance.max_inner_product:
            index_distance = "vector_ip_ops"

        if isinstance(self.index, Ivfflat):
            num_lists = self.index.lists
            if self.index.dynamic_lists:
                total_records = self.get_count()
                logger.debug(f"Number of records: {total_records}")
                if total_records < 1000000:
                    num_lists = int(total_records / 1000)
                elif total_records > 1000000:
                    num_lists = int(sqrt(total_records))

            with self.Session() as sess:
                with sess.begin():
                    logger.debug(f"Setting configuration: {self.index.configuration}")
                    for key, value in self.index.configuration.items():
                        sess.execute(text(f"SET {key} = '{value}';"))
                    logger.debug(
                        f"Creating Ivfflat index with lists: {num_lists}, probes: {self.index.probes} "
                        f"and distance metric: {index_distance}"
                    )
                    sess.execute(text(f"SET ivfflat.probes = {self.index.probes};"))
                    sess.execute(
                        text(
                            f"CREATE INDEX IF NOT EXISTS {self.index.name} ON {self.table} "
                            f"USING ivfflat (embedding {index_distance}) "
                            f"WITH (lists = {num_lists});"
                        )
                    )
        elif isinstance(self.index, HNSW):
            with self.Session() as sess:
                with sess.begin():
                    logger.debug(f"Setting configuration: {self.index.configuration}")
                    for key, value in self.index.configuration.items():
                        sess.execute(text(f"SET {key} = '{value}';"))
                    logger.debug(
                        f"Creating HNSW index with m: {self.index.m}, ef_construction: {self.index.ef_construction} "
                        f"and distance metric: {index_distance}"
                    )
                    sess.execute(
                        text(
                            f"CREATE INDEX IF NOT EXISTS {self.index.name} ON {self.table} "
                            f"USING hnsw (embedding {index_distance}) "
                            f"WITH (m = {self.index.m}, ef_construction = {self.index.ef_construction});"
                        )
                    )
        logger.debug("==== Optimized Vector DB ====")

    def delete(self) -> bool:
        from sqlalchemy import delete

        with self.Session() as sess:
            with sess.begin():
                stmt = delete(self.table)
                sess.execute(stmt)
                return True

    def __deepcopy__(self, memo):
        """
        Create a deep copy of the PgVector instance, handling unpickleable attributes.

        Args:
            memo (dict): A dictionary of objects already copied during the current copying pass.

        Returns:
            PgVector: A deep-copied instance of PgVector.
        """
        from copy import deepcopy

        # Create a new instance without calling __init__
        cls = self.__class__
        copied_obj = cls.__new__(cls)
        memo[id(self)] = copied_obj

        # Deep copy attributes
        for k, v in self.__dict__.items():
            if k in {"metadata", "table"}:
                continue
            # Reuse db_engine and Session without copying
            elif k in {"db_engine", "Session", "embedder"}:
                setattr(copied_obj, k, v)
            else:
                setattr(copied_obj, k, deepcopy(v, memo))

        # Recreate metadata and table for the copied instance
        copied_obj.metadata = MetaData(schema=copied_obj.schema)
        copied_obj.table = copied_obj.get_table()

        return copied_obj
