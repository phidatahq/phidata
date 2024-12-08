from hashlib import md5
from typing import List, Dict, Optional, Any


try:
    from pymongo.mongo_client import MongoClient
    from bson.objectid import ObjectId
except ImportError:
    raise ImportError("The `mongodb` packageis not installed. Please install it using `pip install pymongo`")


from phi.document import Document
from phi.embedder import Embedder
from phi.embedder.openai import OpenAIEmbedder
from phi.vectordb.base import VectorDb
from phi.vectordb.distance import Distance
from phi.utils.log import logger


class MongoDb(VectorDb):
    def __init__(
        self,
        collection: str,
        db_url: Optional[str] = None,
        database: str = "vector_db",
        embedder: Embedder = OpenAIEmbedder(),
        distance: Distance = Distance.cosine,
        **kwargs,
    ):
        self.database: str = database

        self.db = self._client[self.database]

        self.collection: str = collection

        self.embedder: Embedder = embedder

        self.distance: Distance = distance

        self._collection: Optional[Any] = self.db[self.collection]

        self._client: Optional[MongoClient] = None

        self.connection_string: str = db_url

        self.kwargs = kwargs

    @property
    def client(self) -> MongoClient:
        if self._client is None:
            try:
                logger.debug("Creating MongoDB Client")
                self._client = MongoClient(self.connection_string, **self.kwargs)
            except ConnectionRefusedError as e:
                raise ConnectionRefusedError(f"Failed to connect to MongoDB: {e}")
        return self._client

    def create(self) -> None:
        """Create the collection MongoDB"""
        if not self._collection:
            logger.debug(f"Creating collection: {self._collection}")
            self.collection_obj = self.db.create_collection(
                name=self._collection, metadata={"hnsw:space": self.distance.value}
            )
        else:
            logger.debug(f"Collection already exists: {self._collection}")
            self._collection = self._client.get_database

    def doc_exists(self, document: Document) -> bool:
        """Check if a document exists in the MongoDB collection."""
        doc_id = md5(document.content.encode()).hexdigest()
        try:
            exists = self.collection_obj.find_one({"_id": doc_id}) is not None
            logger.debug(f"Document {'exists' if exists else 'does not exist'}: {doc_id}")
            return exists
        except Exception as e:
            logger.error(f"Error checking document existence: {e}")
            return False

    def name_exists(self, name: str) -> bool:
        """Check if a document with a given name exists in the collection."""
        try:
            exists = self.collection_obj.find_one({"name": name}) is not None
            logger.debug(f"Document with name '{name}' {'exists' if exists else 'does not exist'}")
            return exists
        except Exception as e:
            logger.error(f"Error checking document name existence: {e}")
            return False

    def prepare_doc(self, document: Document) -> Dict[str, Any]:
        """Prepare a document for insertion/upsert."""
        document.embed(embedder=self.embedder)
        if document.embedding is None:
            raise ValueError(f"Failed to generate embedding for document: {document.id}")

        cleaned_content = document.content.replace("\x00", "\ufffd")
        doc_id = md5(cleaned_content.encode()).hexdigest()
        doc_data = {
            "_id": doc_id,
            "name": document.name,
            "content": cleaned_content,
            "meta_data": document.meta_data,
            "embedding": document.embedding,
        }
        return doc_data

    def insert(self, documents: List[Document], filters: Optional[Dict[str, Any]] = None) -> None:
        """Insert documents into the MongoDB collection."""
        logger.debug(f"Inserting {len(documents)} documents")

        for document in documents:
            doc_data = self.prepare_doc(document)
            try:
                self.collection_obj.insert_one(doc_data)
                logger.debug(f"Inserted document: {doc_data['_id']} | {document.name} | {document.meta_data}")
            except Exception as e:
                logger.error(f"Error inserting document: {e}")

    def upsert(self, documents: List[Document], filters: Optional[Dict[str, Any]] = None) -> None:
        """Upsert documents into the MongoDB collection."""
        logger.debug(f"Upserting {len(documents)} documents")

        for document in documents:
            doc_data = self.prepare_doc(document)

            result = self.collection_obj.update_one({"_id": doc_data["_id"]}, {"$set": doc_data}, upsert=True)
            if result.upserted_id:
                logger.debug(f"Inserted new document: {doc_data['_id']} | {document.name} | {document.meta_data}")
            else:
                logger.debug(f"Updated existing document: {doc_data['_id']} | {document.name} | {document.meta_data}")
        logger.debug(f"Committed {len(documents)} documents")

    def search(
        self, query: str, limit: int = 5, filters: Optional[Dict[str, Any]] = None, min_score: float = 0.0
    ) -> List[Document]:
        """Search the MongoDB collection for a query."""

        query_embedding = self.embedder.get_embedding(query)
        if query_embedding is None:
            logger.error(f"Failed to generate embedding for query: {query}")
            return []

        search_results: List[Document] = []

        for doc in self.collection_obj.find(filters or {}):
            doc_embedding = doc.get("embedding")
            if doc_embedding is None:
                continue

            distance = self.calculate_distance(query_embedding, doc_embedding)
            score = 1.0 - distance

            if score >= min_score:
                search_results.append(
                    Document(
                        id=str(doc["_id"]),
                        content=doc["content"],
                        meta_data=doc.get("meta_data", {}),
                        distance=distance,
                        score=score,
                    )
                )
            results = sorted(search_results, key=lambda x: x.score, reverse=True)[:limit]
        return results

    def delete(self, doc_ids: List[str]) -> bool:
        """Delete specific documents from the MongoDB collection."""
        try:
            self.collection_obj.delete_many({"_id": {"$in": [ObjectId(doc_id) for doc_id in doc_ids]}})
            return True
        except Exception as e:
            logger.error(f"Error deleting documents: {e}")
            return False

    def exists(self) -> bool:
        """Check if the MongoDB collection exists."""
        return self.collection_obj in self.db.list_collection_names()

    def get_count(self) -> int:
        """Get the count of documents in the MongoDB collection."""
        return self.collection_obj.count_documents({})
