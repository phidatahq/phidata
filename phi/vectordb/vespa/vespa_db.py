from hashlib import md5
from typing import List, Optional, Dict, Any
import json

try:
    import vespa  # type: ignore
except ImportError:
    raise ImportError("`vespa` not installed.")

from phi.document import Document
from phi.embedder import Embedder
from phi.vectordb.base import VectorDb
from phi.vectordb.distance import Distance
from phi.vectordb.search import SearchType
from phi.utils.log import logger
from phi.reranker.base import Reranker


class VespaDb(VectorDb):
    def __init__(
        self,
        uri: str = "http://localhost:8080",
        app_name: Optional[str] = None,
        embedder: Optional[Embedder] = None,
        search_type: SearchType = SearchType.vector,
        distance: Distance = Distance.cosine,
        reranker: Optional[Reranker] = None,
    ):
        # Embedder for embedding the document contents
        if embedder is None:
            from phi.embedder.openai import OpenAIEmbedder

            embedder = OpenAIEmbedder()
        self.embedder: Embedder = embedder
        self.dimensions: Optional[int] = self.embedder.dimensions

        if self.dimensions is None:
            raise ValueError("Embedder.dimensions must be set.")

        # Search type
        self.search_type: SearchType = search_type
        # Distance metric
        self.distance: Distance = distance

        # Vespa connection details
        self.uri: str = uri
        self.app_name: str = app_name or "vespa_app"
        self.connection = vespa.ApplicationPackage(name=self.app_name)

        self.reranker: Optional[Reranker] = reranker

        logger.debug(f"Initialized VespaDb with app: '{self.app_name}'")

    def create(self) -> None:
        """Create the application if it does not exist."""
        if not self.exists():
            self.connection = vespa.Deploy(self.connection, self.uri)

    def doc_exists(self, document: Document) -> bool:
        """
        Validating if the document exists or not

        Args:
            document (Document): Document to validate
        """
        cleaned_content = document.content.replace("\x00", "\ufffd")
        doc_id = md5(cleaned_content.encode()).hexdigest()
        result = self.connection.query(body={"yql": f"select * from sources * where id contains '{doc_id}'"})
        return len(result.hits) > 0

    def insert(self, documents: List[Document], filters: Optional[Dict[str, Any]] = None) -> None:
        """
        Insert documents into the database.

        Args:
            documents (List[Document]): List of documents to insert
            filters (Optional[Dict[str, Any]]): Filters to apply while inserting documents
        """
        logger.debug(f"Inserting {len(documents)} documents")
        data = []
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

        self.connection.feed(data)
        logger.debug(f"Upsert {len(data)} documents")

    def upsert(self, documents: List[Document], filters: Optional[Dict[str, Any]] = None) -> None:
        """
        Upsert documents into the database.

        Args:
            documents (List[Document]): List of documents to upsert
            filters (Optional[Dict[str, Any]]): Filters to apply while upserting
        """
        logger.debug("Redirecting the request to insert")
        self.insert(documents)

    def search(self, query: str, limit: int = 5, filters: Optional[Dict[str, Any]] = None) -> List[Document]:
        if self.search_type == SearchType.vector:
            return self.vector_search(query, limit)
        elif self.search_type == SearchType.keyword:
            return self.keyword_search(query, limit)
        elif self.search_type == SearchType.hybrid:
            return self.hybrid_search(query, limit)
        else:
            logger.error(f"Invalid search type '{self.search_type}'.")
            return []

    def vector_search(self, query: str, limit: int = 5) -> List[Document]:
        query_embedding = self.embedder.get_embedding(query)
        if query_embedding is None:
            logger.error(f"Error getting embedding for Query: {query}")
            return []

        results = self.connection.query(
            body={"yql": f"select * from sources * where vector contains '{query_embedding}' limit {limit}"}
        )

        search_results = self._build_search_results(results.hits)

        if self.reranker:
            search_results = self.reranker.rerank(query=query, documents=search_results)

        return search_results

    def hybrid_search(self, query: str, limit: int = 5) -> List[Document]:
        query_embedding = self.embedder.get_embedding(query)
        if query_embedding is None:
            logger.error(f"Error getting embedding for Query: {query}")
            return []

        results = self.connection.query(
            body={
                "yql": f"select * from sources * where vector contains '{query_embedding}' and text contains '{query}' limit {limit}"
            }
        )

        search_results = self._build_search_results(results.hits)

        if self.reranker:
            search_results = self.reranker.rerank(query=query, documents=search_results)

        return search_results

    def keyword_search(self, query: str, limit: int = 5) -> List[Document]:
        results = self.connection.query(
            body={"yql": f"select * from sources * where text contains '{query}' limit {limit}"}
        )
        search_results = self._build_search_results(results.hits)

        if self.reranker:
            search_results = self.reranker.rerank(query=query, documents=search_results)
        return search_results

    def _build_search_results(self, results) -> List[Document]:
        search_results: List[Document] = []
        try:
            for item in results:
                payload = json.loads(item["fields"]["payload"])
                search_results.append(
                    Document(
                        name=payload["name"],
                        meta_data=payload["meta_data"],
                        content=payload["content"],
                        embedder=self.embedder,
                        embedding=item["fields"]["vector"],
                        usage=payload["usage"],
                    )
                )

        except Exception as e:
            logger.error(f"Error building search results: {e}")

        return search_results

    def drop(self) -> None:
        if self.exists():
            logger.debug(f"Deleting application: {self.app_name}")
            self.connection.delete_application()

    def exists(self) -> bool:
        try:
            self.connection.get_application_status()
            return True
        except vespa.VespaConnectionError:  # Specify the exception type
            return False

    def get_count(self) -> int:
        if self.exists():
            result = self.connection.query(body={"yql": "select count(*) from sources *"})
            return result.hits[0]["fields"]["count"]
        return 0

    def optimize(self) -> None:
        pass

    def delete(self) -> bool:
        return False

    def name_exists(self, name: str) -> bool:
        raise NotImplementedError
