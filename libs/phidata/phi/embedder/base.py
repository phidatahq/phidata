from typing import Optional, Dict, List, Tuple

from pydantic import BaseModel, ConfigDict


class Embedder(BaseModel):
    """Base class for managing embedders"""

    dimensions: Optional[int] = 1536

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def get_embedding(self, text: str) -> List[float]:
        raise NotImplementedError

    def get_embedding_and_usage(self, text: str) -> Tuple[List[float], Optional[Dict]]:
        raise NotImplementedError
