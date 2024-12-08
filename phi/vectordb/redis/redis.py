import os
import json
from hashlib import md5
from typing import Optional, List, Union, Dict, Any
from pydantic import PrivateAttr

try:
    import redis
    from redis.exceptions import RedisError
except ImportError:
    raise ImportError("The `redis` package is not installed. " "Please install it via `pip install redis`.")

try:
    from redisvl.index import SearchIndex
    from redisvl.schema import IndexSchema
    from redisvl.query import VectorQuery, CountQuery
    from redisvl.query.filter import Tag
except ImportError:
    raise ImportError("The `redisvl` package is not installed. " "Please install it via `pip install redisvl`.")


from phi.vectordb.base import VectorDB
from phi.embedder import Embedder
from phi.document import Document
from phi.utils.log import logger
from phi.vectordb.redis.schema import (
    NODE_ID_FIELD_NAME,
    DOC_ID_FIELD_NAME,
    TEXT_FIELD_NAME,
    NODE_CONTENT_FIELD_NAME,
    VECTOR_FIELD_NAME,
    RedisVectorStoreSchema,
)


class Redis(VectorDB):
    _index: SearchIndex = PrivateAttr()
    _overwrite: bool = PrivateAttr()
    _return_fields: List[str] = PrivateAttr()

    def __init__(
        self,
        redis_url: Optional[str] = None,
        redis_client: Optional[redis.Redis] = None,
        embedder: Optional[Embedder] = None,
        index_schema: Optional[Union[Dict[str, List[Dict]], str, os.PathLike]] = None,
        overwrite: bool = False,
        return_fields: Optional[List[str]] = None,
        **kwargs,
    ):
        self._flag_old_kwargs(**kwargs)
        super().__init__()

        if not index_schema:
            logger.info("Using default RedisVectorStore Schema.")
            index_schema = RedisVectorStoreSchema()

        self._validate_schema(index_schema)
        self._return_fields = return_fields or [
            NODE_ID_FIELD_NAME,
            DOC_ID_FIELD_NAME,
            TEXT_FIELD_NAME,
            NODE_CONTENT_FIELD_NAME,
        ]
        self._overwrite = overwrite

        self._index = SearchIndex(schema=index_schema)

        if redis_client:
            self._index.set_client(redis_client)
        elif redis_url:
            self._index.connect(redis_url)
        else:
            raise ValueError("Failed to connect to Redis. Must provide a valid redis client or url")

        self.create()

        if embedder is None:
            from phi.embedder.openai import OpenAIEmbedder

            embedder = OpenAIEmbedder()

        self.embedder: Embedder = embedder

    def _flag_old_kwargs(self, **kwargs):
        old_kwargs = ["index_name", "index_prefix", "prefix_ending", "index_args", "metadata_fields"]

        for kwarg in old_kwargs:
            if kwarg in kwargs:
                logger.warning(
                    f"Using deprecated argument {kwarg}. RedisVectorStore now requires an IndexSchema object.See the documentation for a complete example: https://docs.llamaindex.ai/en/stable/examples/vector_stores/RedisIndexDemo/"
                )

    def _validate_schema(self, schema: IndexSchema) -> str:
        base_schema = IndexSchema()
        for name, field in base_schema.fields.items():
            if (name not in schema.fields) or (not schema.fields[name].type == field.type):
                raise ValueError(
                    f"Required field {name} must be present in the index" f"and of type {schema.fields[name].type}"
                )

    def create(self, overwrite: Optional[bool] = None) -> None:
        """Create an index in Redis."""

        if overwrite is None:
            overwrite = self._overwrite

        try:
            if overwrite:
                self._index.create(overwrite=True, drop=True)
            else:
                self._index.create()
        except RedisError as e:
            if "Index already exists" in str(e) and not overwrite:
                raise RuntimeError("The index already exists and 'overwrite' is False.") from e
            raise e
        except ValueError as e:
            if "No fields defined" in str(e):
                raise ValueError("No fields are defined for the index.") from e
            raise e

    def insert(self, documents: List[Document], filters: Optional[Dict[str, Any]] = None) -> None:
        """Insert documents into the index."""

        if len(documents) == 0:
            raise ValueError("No documents to insert.")

        embedding_len = len(documents[0].embed())
        expected_dims = self._index.schema.fields[VECTOR_FIELD_NAME].attrs.dims
        if embedding_len != expected_dims:
            raise ValueError(f"Expected embedding length of {expected_dims}, got {embedding_len}")
        data: List[Dict[str, Any]] = []

        for document in documents:
            document.embed(embedder=self.embedder)
            cleaned_content = document.content.replace("\x00", "\ufffd")
            doc_id = str(md5(cleaned_content.encode()).hexdigest())
            payload = {
                "name": document.name,
                "meta_data": document.meta_data,
                "content": cleaned_content,
                "usage": document.usage,
            }
            data.append(
                {
                    "id": doc_id,
                    "vector": document.embedding,
                    "payload": json.dumps(payload),
                }
            )
            logger.debug(f"Inserted document: {document.name} ({document.meta_data})")
        self._index.load(data, filters=filters)

    def doc_exists(self, document: Document) -> bool:
        """Check if a document exists in the index."""
        doc_filter = Tag(DOC_ID_FIELD_NAME) == document.id
        total = self._index.query(CountQuery(filter=doc_filter))
        return total > 0

    def name_exists(self, name: str) -> bool:
        # return self._index.exists(name)
        pass

    def exists(self) -> bool:
        self._index.exists()

    def delete(self, document: Document) -> bool:
        pass

    def drop(self, drop: bool = True) -> bool:
        try:
            self._index.delete(drop=drop)
            logger.info(f"Index {self._index.name} deleted successfully.")
            return True
        except RedisError as e:
            logger.error(f"Failed to delete index {self._index.name}: {str(e)}")
            raise e

    def upsert(self, documents: List[Document], filters: Optional[Dict[str, Any]] = None) -> None:
        return self.insert(documents, filters=filters)

    def search(self, query: str, limit: int = 5, filters: Optional[Dict[str, Any]] = None) -> List[Document]:
        query_embedding = self.embedder.get_embedding(query)
        if query_embedding is None:
            logger.error(f"Error getting embedding for Query: {query}")
            return []

        query = VectorQuery(
            query_vector=query_embedding,
            vector_field_name=VECTOR_FIELD_NAME,
            # filter_expression=filters,
            num_results=limit,
        )

        results = self._index.query(query)

        search_results: List[Document] = []
        for result in results:
            if result.payload is None:
                continue
            search_results.append(
                Document(
                    name=result.paylor["name"],
                    meta_data=result.payload["meta_data"],
                    content=result.payload["content"],
                    embedder=self.embedder,
                    embedding=result.vector,
                    usage=result.payload["usage"],
                )
            )
        return search_results
