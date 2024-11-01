from typing import List, Tuple, Optional, Dict
from phi.embedder.base import Embedder
from phi.utils.log import logger

try:
    from fastembed import TextEmbedding # type: ignore

except ImportError:
    raise ImportError("fastembed not installed, use pip install fastembed")


class FastEmbedEmbedder(Embedder):
    model: str = "BAAI/bge-small-en-v1.5"
    dimensions: int = 384

    def get_embedding(self, text: str) -> List[float]:
        model = TextEmbedding(model_name=self.model)
        embeddings = model.embed(text)
        embedding_list = list(embeddings)

        try:
            return embedding_list
        except Exception as e:
            logger.warning(e)
            return []

    def get_embedding_and_usage(self, text) -> Tuple[List[float], Optional[Dict]]:
        return super().get_embedding_and_usage(text)
