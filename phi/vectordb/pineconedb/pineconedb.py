from typing import Optional, Dict, Config, Union, List

try:
    from pinecone import Pinecone
except ImportError:
    raise ImportError(
        "The `pinecone-client` package is not installed. "
        "Please install it via `pip install pinecone-client`."
    )

from phi.document import Document
from phi.vectordb.base import VectorDb
from phi.utils.log import logger
from pinecone.core.client.api.manage_indexes_api import ManageIndexesApi
from pinecone.models import ServerlessSpec, PodSpec

class PineconeDB(VectorDb):
    def __init__(
        self,
        name: str,
        dimension: int,
        spec: Union[Dict, ServerlessSpec, PodSpec],
        metric: Optional[str] = "cosine",
        additional_headers: Optional[Dict[str, str]] = {},
        pool_threads: Optional[int] = 1,
        timeout: Optional[int] = None,
        index_api: Optional[ManageIndexesApi] = None,
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
        self.additional_headers: Optional[Dict[str, str]] = additional_headers
        self.pool_threads: Optional[int] = pool_threads
        self.index_api: Optional[ManageIndexesApi] = index_api
        self.name: str = name
        self.dimension: int = dimension
        self.spec: Union[Dict, ServerlessSpec, PodSpec] = spec
        self.metric: Optional[str] = metric
        self.timeout: Optional[int] = timeout
        self.kwargs: Optional[Dict[str, str]] = kwargs

    @property
    def client(self) -> Pinecone:
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
        if self._index is None:
            logger.debug(f"Connecting to Pinecone Index: {self.name}")
            self._index = self.client.Index(self.name)
        return self._index

    def exists(self) -> bool:
        list_indexes = self.client.list_indexes()
        return self.name in list_indexes.names()

    def create(self) -> None:
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
        if self.exists():
            logger.debug(f"Deleting index: {self.name}")
            self.client.delete_index(name=self.name, timeout=self.timeout)

    def doc_exists(self, document: Document) -> bool:
        response = self.index.fetch(ids=[document.id])
        return len(response.vectors) > 0

    def name_exists(self, name: str) -> bool:
        try:
            self.client.describe_index(name)
            return True
        except Exception:
            return False

    def upsert(self, documents: List[Document], namespace: Optional[str] = None, batch_size: Optional[int] = None, show_progress: bool = False) -> None:
        vectors = [{"id": doc.id, "values": doc.embedding, "metadata": doc.metadata} for doc in documents]
        self.index.upsert(vectors=vectors, namespace=namespace, batch_size=batch_size, show_progress=show_progress)

    def upsert_available(self) -> bool:
        return True

    def insert(self, documents: List[Document]) -> None:
        raise NotImplementedError("Pinecone does not support insert operations. Use upsert instead.")

    def search(self, query_vector: List[float], limit: int = 5, namespace: Optional[str] = None, filter: Optional[Dict[str, Union[str, float, int, bool, List, dict]]] = None, include_values: Optional[bool] = None, include_metadata: Optional[bool] = None) -> List[Document]:
        response = self.index.query(
            vector=query_vector,
            top_k=limit,
            namespace=namespace,
            filter=filter,
            include_values=include_values,
            include_metadata=include_metadata,
        )
        return [Document(id=result.id, embedding=result.values, metadata=result.metadata) for result in response.matches]

    def optimize(self) -> None:
        pass  # Pinecone automatically optimizes indexes, so this method can be left empty

    def clear(self, namespace: Optional[str] = None) -> None:
        self.index.delete(delete_all=True, namespace=namespace)