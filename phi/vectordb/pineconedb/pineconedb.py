from typing import Optional, Dict, Union, List, Any

try:
    from pinecone import Pinecone
    from pinecone.config import Config
except ImportError:
    raise ImportError(
        "The `pinecone-client` package is not installed, please install using `pip install pinecone-client`."
    )

from phi.document import Document
from phi.embedder import Embedder
from phi.vectordb.base import VectorDb
from phi.utils.log import logger
from pinecone.models import ServerlessSpec, PodSpec
from pinecone.core.openapi.data.model.vector import Vector


class PineconeDB(VectorDb):
    """A class representing a Pinecone database.

    Args:
        name (str): The name of the index.
        dimension (int): The dimension of the embeddings.
        spec (Union[Dict, ServerlessSpec, PodSpec]): The index spec.
        metric (Optional[str], optional): The metric used for similarity search. Defaults to "cosine".
        additional_headers (Optional[Dict[str, str]], optional): Additional headers to pass to the Pinecone client. Defaults to {}.
        pool_threads (Optional[int], optional): The number of threads to use for the Pinecone client. Defaults to 1.
        timeout (Optional[int], optional): The timeout for Pinecone operations. Defaults to None.
        index_api (Optional[Any], optional): The Index API object. Defaults to None.
        api_key (Optional[str], optional): The Pinecone API key. Defaults to None.
        host (Optional[str], optional): The Pinecone host. Defaults to None.
        config (Optional[Config], optional): The Pinecone config. Defaults to None.
        **kwargs: Additional keyword arguments.

    Attributes:
        client (Pinecone): The Pinecone client.
        index: The Pinecone index.
        api_key (Optional[str]): The Pinecone API key.
        host (Optional[str]): The Pinecone host.
        config (Optional[Config]): The Pinecone config.
        additional_headers (Optional[Dict[str, str]]): Additional headers to pass to the Pinecone client.
        pool_threads (Optional[int]): The number of threads to use for the Pinecone client.
        index_api (Optional[Any]): The Index API object.
        name (str): The name of the index.
        dimension (int): The dimension of the embeddings.
        spec (Union[Dict, ServerlessSpec, PodSpec]): The index spec.
        metric (Optional[str]): The metric used for similarity search.
        timeout (Optional[int]): The timeout for Pinecone operations.
        kwargs (Optional[Dict[str, str]]): Additional keyword arguments.
    """

    def __init__(
        self,
        name: str,
        dimension: int,
        spec: Union[Dict, ServerlessSpec, PodSpec],
        embedder: Optional[Embedder] = None,
        metric: Optional[str] = "cosine",
        additional_headers: Optional[Dict[str, str]] = None,
        pool_threads: Optional[int] = 1,
        namespace: Optional[str] = None,
        timeout: Optional[int] = None,
        index_api: Optional[Any] = None,
        api_key: Optional[str] = None,
        host: Optional[str] = None,
        config: Optional[Config] = None,
        **kwargs,
    ):
        self._client = None
        self._index = None
        self.api_key: Optional[str] = api_key
        self.host: Optional[str] = host
        self.config: Optional[Config] = config
        self.additional_headers: Dict[str, str] = additional_headers or {}
        self.pool_threads: Optional[int] = pool_threads
        self.namespace: Optional[str] = namespace
        self.index_api: Optional[Any] = index_api
        self.name: str = name
        self.dimension: Optional[int] = dimension
        self.spec: Union[Dict, ServerlessSpec, PodSpec] = spec
        self.metric: Optional[str] = metric
        self.timeout: Optional[int] = timeout
        self.kwargs: Optional[Dict[str, str]] = kwargs

        # Embedder for embedding the document contents
        _embedder = embedder
        if _embedder is None:
            from phi.embedder.openai import OpenAIEmbedder

            _embedder = OpenAIEmbedder()
        self.embedder: Embedder = _embedder

    @property
    def client(self) -> Pinecone:
        """The Pinecone client.

        Returns:
            Pinecone: The Pinecone client.

        """
        if self._client is None:
            logger.debug("Creating Pinecone Client")
            self._client = Pinecone(
                api_key=self.api_key,
                host=self.host,
                config=self.config,
                additional_headers=self.additional_headers,
                pool_threads=self.pool_threads,
                index_api=self.index_api,
                **self.kwargs,
            )
        return self._client

    @property
    def index(self):
        """The Pinecone index.

        Returns:
            Pinecone.Index: The Pinecone index.

        """
        if self._index is None:
            logger.debug(f"Connecting to Pinecone Index: {self.name}")
            self._index = self.client.Index(self.name)
        return self._index

    def exists(self) -> bool:
        """Check if the index exists.

        Returns:
            bool: True if the index exists, False otherwise.

        """
        list_indexes = self.client.list_indexes()
        return self.name in list_indexes.names()

    def create(self) -> None:
        """Create the index if it does not exist."""
        if not self.exists():
            logger.debug(f"Creating index: {self.name}")
            self.client.create_index(
                name=self.name,
                dimension=self.dimension,
                spec=self.spec,
                metric=self.metric if self.metric is not None else "cosine",
                timeout=self.timeout,
            )

    def delete(self) -> None:
        """Delete the index if it exists."""
        if self.exists():
            logger.debug(f"Deleting index: {self.name}")
            self.client.delete_index(name=self.name, timeout=self.timeout)

    def doc_exists(self, document: Document) -> bool:
        """Check if a document exists in the index.

        Args:
            document (Document): The document to check.

        Returns:
            bool: True if the document exists, False otherwise.

        """
        response = self.index.fetch(ids=[document.id])
        return len(response.vectors) > 0

    def name_exists(self, name: str) -> bool:
        """Check if an index with the given name exists.

        Args:
            name (str): The name of the index.

        Returns:
            bool: True if the index exists, False otherwise.

        """
        try:
            self.client.describe_index(name)
            return True
        except Exception:
            return False

    def upsert(
        self,
        documents: List[Document],
        namespace: Optional[str] = None,
        batch_size: Optional[int] = None,
        show_progress: bool = False,
    ) -> None:
        """insert documents into the index.

        Args:
            documents (List[Document]): The documents to upsert.
            namespace (Optional[str], optional): The namespace for the documents. Defaults to None.
            batch_size (Optional[int], optional): The batch size for upsert. Defaults to None.
            show_progress (bool, optional): Whether to show progress during upsert. Defaults to False.

        """

        vectors = []
        for document in documents:
            document.embed(embedder=self.embedder)
            document.meta_data["text"] = document.content
            vectors.append(
                Vector(
                    id=document.id,
                    values=document.embedding,
                    metadata=document.meta_data,
                )
            )
        self.index.upsert(
            vectors=vectors,
            namespace=namespace,
            batch_size=batch_size,
            show_progress=show_progress,
        )

    def upsert_available(self) -> bool:
        """Check if upsert operation is available.

        Returns:
            bool: True if upsert is available, False otherwise.

        """
        return True

    def insert(self, documents: List[Document]) -> None:
        """Insert documents into the index.

        This method is not supported by Pinecone. Use `upsert` instead.

        Args:
            documents (List[Document]): The documents to insert.

        Raises:
            NotImplementedError: This method is not supported by Pinecone.

        """
        raise NotImplementedError("Pinecone does not support insert operations. Use upsert instead.")

    def search(
        self,
        query: str,
        limit: int = 5,
        namespace: Optional[str] = None,
        filter: Optional[Dict[str, Union[str, float, int, bool, List, dict]]] = None,
        include_values: Optional[bool] = None,
    ) -> List[Document]:
        """Search for similar documents in the index.

        Args:
            query (str): The query to search for.
            limit (int, optional): The maximum number of results to return. Defaults to 5.
            namespace (Optional[str], optional): The namespace to search in. Defaults to None.
            filter (Optional[Dict[str, Union[str, float, int, bool, List, dict]]], optional): The filter for the search. Defaults to None.
            include_values (Optional[bool], optional): Whether to include values in the search results. Defaults to None.
            include_metadata (Optional[bool], optional): Whether to include metadata in the search results. Defaults to None.

        Returns:
            List[Document]: The list of matching documents.

        """
        query_embedding = self.embedder.get_embedding(query)

        if query_embedding is None:
            logger.error(f"Error getting embedding for Query: {query}")
            return []

        response = self.index.query(
            vector=query_embedding,
            top_k=limit,
            namespace=namespace,
            filter=filter,
            include_values=include_values,
            include_metadata=True,
        )
        return [
            Document(
                content=(result.metadata.get("text", "") if result.metadata is not None else ""),
                id=result.id,
                embedding=result.values,
                meta_data=result.metadata,
            )
            for result in response.matches
        ]

    def optimize(self) -> None:
        """Optimize the index.

        This method can be left empty as Pinecone automatically optimizes indexes.

        """
        pass

    def clear(self, namespace: Optional[str] = None) -> bool:
        """Clear the index.

        Args:
            namespace (Optional[str], optional): The namespace to clear. Defaults to None.

        """
        try:
            self.index.delete(delete_all=True, namespace=namespace)
            return True
        except Exception:
            return False
