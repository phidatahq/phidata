from typing import Optional, Dict, Union, List, Any

try:
    import weaviate
    import weaviate.classes as wvc
    from wvc.config import Configure, Property, DataType
    from Configure import Vectorizer, Generative
except ImportError:
    raise ImportError("The `weaviate` package is not installed, please install using `pip install weaviate-client`.")

from phi.document import Document
from phi.embedder import Embedder
from phi.vectordb.base import VectorDb
from phi.utils.log import logger

class WeaviateDB(VectorDb):
    def __init__(
        self,
        name: str,
        dimension: int,
        url: Optional[str] = None,
        api_key: Optional[str] = None,
        additional_headers: Optional[Dict[str, str]] = None,
        vectorizer_config: Optional[Vectorizer] = None,
        generative_config: Optional[Generative] = None,
        properties: Optional[List[Property]] = None,
        batch_size: Optional[int] = 100
    ):
        self._client = None
        self._index = None
        self.name: str = name
        self.api_key: Optional[str] = api_key
        self.url: Optional[str] = url
        self.dimension: int = dimension
        self.additional_headers: Optional[Dict[str, str]] = additional_headers
        self.vectorizer_config: Optional[Vectorizer] = vectorizer_config
        self.generative_config: Optional[Generative] = generative_config
        self.properties: Optional[List[Property]] = properties
        self.batch_size: int = batch_size
    
    @property
    def client(self) -> weaviate:
        if self._client is None:
            logger.debug("Creating Weaviate Client")
            self._client = weaviate.connect_to_weaviate_cloud(
                cluster_url=self.url,                                  
                auth_credentials=wvc.init.Auth.api_key(self.api_key),
                headers=self.additional_headers 
            )
        return self._client

    def exists(self) -> bool:
        list_collections = self.client.collections.list_all(simple=False)
        return self.name in list_collections
    
    def create(self) -> None:
        """Create the collection if it does not exist."""
        if not self.exists():
            logger.debug(f"Creating collection: {self.name}")

            self.client.collections.create(
                name=self.name,
                vectorizer_config = self.vectorizer_config,
                generative_config = self.generative_config,
                properties = self.properties
            )
    
    def drop(self) -> None:
        """Delete the collection if it exists."""
        if self.exists():
            logger.debug(f"Deleting collection: {self.name}")
            self.client.collections.delete(self.name)
    