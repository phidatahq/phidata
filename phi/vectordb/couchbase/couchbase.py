from typing import List, Optional, Dict, Any
from hashlib import md5

try:
    from couchbase.cluster import Cluster, ClusterOptions
    from couchbase.auth import PasswordAuthenticator
    from couchbase.collection import Collection
    from couchbase.exceptions import CouchbaseException
except ImportError:
    raise ImportError("The `couchbase` package is not installed. Please install it via `pip install couchbase`.")

from phi.document import Document
from phi.embedder import Embedder
from phi.embedder.openai import OpenAIEmbedder
from phi.vectordb.base import VectorDb
from phi.utils.log import logger


class CouchbaseVectorDb(VectorDb):
    def __init__(
        self,
        bucket_name: str,
        collection_name: str,
        username: str,
        password: str,
        host: str = "localhost",
        embedder: Embedder = OpenAIEmbedder(),
    ):
        self.bucket_name = bucket_name
        self.collection_name = collection_name
        self.username = username
        self.password = password
        self.host = host
        self.embedder = embedder

        self.cluster = Cluster(f"couchbase://{self.host}", ClusterOptions(PasswordAuthenticator(self.username, self.password)))
        self.bucket = self.cluster.bucket(self.bucket_name)
        self.collection = self.bucket.collection(self.collection_name)

    def create(self) -> None:
        logger.debug(f"Creating collection: {self.collection_name}")
        try:
            self.bucket.collections().create_scope(self.collection_name)
        except CouchbaseException as e:
            logger.error(f"Error creating collection: {e}")

    def doc_exists(self, document: Document) -> bool:
        doc_id = md5(document.content.encode()).hexdigest()
        try:
            self.collection.get(doc_id)
            return True
        except CouchbaseException:
            return False

    def name_exists(self, name: str) -> bool:
        query = f"SELECT META().id FROM `{self.bucket_name}`.`{self.collection_name}` WHERE name = $1"
        try:
            result = self.cluster.query(query, name)
            return len(result.rows()) > 0
        except CouchbaseException as e:
            logger.error(f"Error checking if name exists: {e}")
            return False

    def insert(self, documents: List[Document], filters: Optional[Dict[str, Any]] = None) -> None:
        for document in documents:
            document.embed(embedder=self.embedder)
            doc_id = md5(document.content.encode()).hexdigest()
            try:
                self.collection.upsert(doc_id, {
                    "name": document.name,
                    "meta_data": document.meta_data,
                    "content": document.content,
                    "embedding": document.embedding,
                    "usage": document.usage,
                })
                logger.debug(f"Inserted document: {document.name} ({document.meta_data})")
            except CouchbaseException as e:
                logger.error(f"Error inserting document: {e}")

    def upsert(self, documents: List[Document], filters: Optional[Dict[str, Any]] = None) -> None:
        self.insert(documents, filters)

    def search(self, query: str, limit: int = 5, filters: Optional[Dict[str, Any]] = None) -> List[Document]:
        query_embedding = self.embedder.get_embedding(query)
        if query_embedding is None:
            logger.error(f"Error getting embedding for Query: {query}")
            return []

        search_query = f"SELECT META().id, name, meta_data, content, embedding, usage FROM `{self.bucket_name}`.`{self.collection_name}` WHERE embedding IS NOT NULL LIMIT {limit}"
        try:
            result = self.cluster.query(search_query)
            search_results = []
            for row in result.rows():
                search_results.append(
                    Document(
                        id=row["id"],
                        name=row["name"],
                        meta_data=row["meta_data"],
                        content=row["content"],
                        embedding=row["embedding"],
                        usage=row["usage"],
                    )
                )
            return search_results
        except CouchbaseException as e:
            logger.error(f"Error searching documents: {e}")
            return []

    def drop(self) -> None:
        logger.debug(f"Dropping collection: {self.collection_name}")
        try:
            self.bucket.collections().drop_scope(self.collection_name)
        except CouchbaseException as e:
            logger.error(f"Error dropping collection: {e}")

    def exists(self) -> bool:
        try:
            self.bucket.collections().get_scope(self.collection_name)
            return True
        except CouchbaseException:
            return False

    def delete(self) -> bool:
        logger.debug(f"Deleting all documents in collection: {self.collection_name}")
        try:
            self.bucket.collections().drop_scope(self.collection_name)
            return True
        except CouchbaseException as e:
            logger.error(f"Error deleting documents: {e}")
            return False
