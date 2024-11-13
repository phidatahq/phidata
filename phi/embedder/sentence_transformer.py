import platform
from typing import Dict, List, Optional, Tuple, Union

from phi.embedder.base import Embedder
from phi.utils.log import logger

try:
    from sentence_transformers import SentenceTransformer

    if platform.system() == "Windows":
        import numpy as np

        numpy_version = np.__version__
        if numpy_version.startswith("2"):
            raise RuntimeError(
                "Incompatible NumPy version detected. Please install NumPy 1.x by running 'pip install numpy<2'."
            )
except ImportError:
    raise ImportError("sentence-transformers not installed, please run pip install sentence-transformers")


class SentenceTransformerEmbedder(Embedder):
    model: str = "sentence-transformers/all-MiniLM-L6-v2"
    sentence_transformer_client: Optional[SentenceTransformer] = None

    def get_embedding(self, text: Union[str, List[str]]) -> List[float]:
        model = SentenceTransformer(model_name_or_path=self.model)
        embedding = model.encode(text)
        try:
            return embedding
        except Exception as e:
            logger.warning(e)
            return []

    def get_embedding_and_usage(self, text: str) -> Tuple[List[float], Optional[Dict]]:
        return self.get_embedding(text=text), None
