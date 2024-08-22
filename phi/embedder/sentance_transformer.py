from typing import Dict, List, Optional, Tuple

from phi.embedder.base import Embedder
from phi.utils.log import logger

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    raise ImportError("`sentence-transformers` not installed, please run `pip install sentence-transformers`")


class SentenceTransformerEmbedder(Embedder):
    model: str = "sentence-transformers/all-MiniLM-L6-v2"
    sentence_transformer_client: Optional[SentenceTransformer] = None

    def get_embedding(self, text: str | List[str]) -> List[float]:
        model = SentenceTransformer(model_name_or_path=self.model)
        embedding = model.encode(text)
        try:
            return embedding
        except Exception as e:
            logger.warning(e)
            return []

    def get_embedding_and_usage(self, text: str) -> Tuple[List[float], Dict | None]:
        return super().get_embedding_and_usage(text)
