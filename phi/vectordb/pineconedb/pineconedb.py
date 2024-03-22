from typing import Optional, Dict, Config, Union

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

    def exists(self) -> bool:
        list_indexes = self._client.list_indexes()
        if self.name in list_indexes:
            return True

    def create(self) -> None:
        if not self.exists():
            logger.debug(f"Creating index: {self.name}")
            self._client.create_index(
                name=self.name,
                dimension=self.dimension,
                spec=self.spec,
                metric=self.metric if self.metric is not None else "cosine",
                timeout=self.timeout,
            )