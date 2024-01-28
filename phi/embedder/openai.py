from typing import Optional, Dict, List, Tuple, Any
from typing_extensions import Literal

from phi.embedder.base import Embedder
from phi.utils.env import get_from_env
from phi.utils.log import logger

try:
    from openai import OpenAI
    from openai.types.create_embedding_response import CreateEmbeddingResponse
except ImportError:
    raise ImportError("`openai` not installed")


class OpenAIEmbedder(Embedder):
    model: str = "text-embedding-ada-002"
    dimensions: int = 1536
    encoding_format: Literal["float", "base64"] = "float"
    user: Optional[str] = None
    openai: Optional[OpenAI] = None

    @property
    def client(self) -> OpenAI:
        return self.openai or OpenAI()

    def _response(self, text: str) -> CreateEmbeddingResponse:
        params: Dict[str, Any] = {
            "input": text,
            "model": self.model,
            "encoding_format": self.encoding_format,
        }
        if self.user is not None:
            params["user"] = self.user
        if self.model.startswith("text-embedding-3"):
            params["dimensions"] = self.dimensions

        if get_from_env("OPENAI_API_KEY") is None:
            logger.debug("--o-o-- Using phi-proxy")
            try:
                from phi.api.llm import openai_embedding

                response_json = openai_embedding(params=params)
                if response_json is None:
                    logger.error("Error: Could not reach Phidata Servers.")
                    logger.info("Please message us on https://discord.gg/4MtYHHrgA8 for help.")
                    exit(1)
                else:
                    return CreateEmbeddingResponse.model_validate_json(response_json)
            except Exception as e:
                logger.exception(e)
                logger.info("Please message us on https://discord.gg/4MtYHHrgA8 for help.")
                exit(1)
        else:
            return self.client.embeddings.create(**params)

    def get_embedding(self, text: str) -> List[float]:
        response: CreateEmbeddingResponse = self._response(text=text)
        try:
            return response.data[0].embedding
        except Exception as e:
            logger.warning(e)
            return []

    def get_embedding_and_usage(self, text: str) -> Tuple[List[float], Optional[Dict]]:
        response: CreateEmbeddingResponse = self._response(text=text)

        embedding = response.data[0].embedding
        usage = response.usage
        return embedding, usage.model_dump()
