from typing import Optional, Dict, List, Tuple

from phi.embedder.base import Embedder
from phi.utils.env import get_from_env
from phi.utils.log import logger

try:
    from openai import Embedding  # noqa: F401
except ImportError:
    raise ImportError("`openai` not installed")


class OpenAIEmbedder(Embedder):
    model: str = "text-embedding-ada-002"
    dimensions: int = 1536

    def _response(self, text: str):
        if get_from_env("OPENAI_API_KEY") is None:
            logger.debug("--o-o-- Using Phidata Servers")
            try:
                from phi.api.llm import openai_embedding

                response_dict = openai_embedding(
                    params={
                        "input": text,
                        "model": self.model,
                    }
                )
                return response_dict
            except Exception as e:
                logger.exception(e)
                logger.info("Please message us on https://discord.gg/4MtYHHrgA8 for help.")
                exit(1)
        else:
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
