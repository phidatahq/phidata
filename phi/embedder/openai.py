from typing import Optional, Dict, List, Tuple

from phi.embedder.base import Embedder


class OpenAIEmbedder(Embedder):
    model: str = "text-embedding-ada-002"
    dimensions: int = 1536

    def _response(self, text: str):
        try:
            from openai import Embedding  # noqa: F401
        except ImportError:
            raise ImportError("`openai` not installed")

        return Embedding.create(input=text, model=self.model)

    def get_embedding(self, text: str) -> List[float]:
        response = self._response(text=text)
        if "data" not in response:
            return []

        return response["data"][0]["embedding"]

    def get_embedding_and_usage(self, text: str) -> Tuple[List[float], Optional[Dict]]:
        response = self._response(text=text)
        if "data" not in response:
            return [], None

        embedding = response["data"][0]["embedding"]
        usage = response.get("usage", None)
        return embedding, usage
