from enum import Enum
from typing import Any, Dict, List
from phi.vectordb.distance import Distance

from redisvl.schema import IndexSchema, IndexInfo, StorageType

NODE_ID_FIELD_NAME: str = "id"
DOC_ID_FIELD_NAME: str = "doc_id"
TEXT_FIELD_NAME: str = "text"
NODE_CONTENT_FIELD_NAME: str = "_node_content"
VECTOR_FIELD_NAME: str = "vector"


class Algorithm(Enum):
    FLAT = "flat"
    HSNW = "hsnw"


class RedisIndexInfo(IndexInfo):
    """The default Redis Vector Store Index Info."""

    name: str = "phidata"
    """The unique name of the index."""
    prefix: str = "phidata/vector"
    """The prefix used for Redis keys associated with this index."""
    key_separator: str = "_"
    """The separator character used in designing Redis keys."""
    storage_type: StorageType = StorageType.HASH
    """The storage type used in Redis (e.g., 'hash' or 'json')."""


class RedisVectorStoreSchema(IndexSchema):
    """The default Redis Vector Store Schema."""

    def __init__(self, **data) -> None:
        index = RedisIndexInfo()
        fields: List[Dict[str, Any]] = [
            {"type": "tag", "name": NODE_ID_FIELD_NAME, "attrs": {"sortable": False}},
            {"type": "tag", "name": DOC_ID_FIELD_NAME, "attrs": {"sortable": False}},
            {"type": "text", "name": TEXT_FIELD_NAME, "attrs": {"weight": 1.0}},
            {
                "type": "vector",
                "name": VECTOR_FIELD_NAME,
                "attrs": {
                    "dims": 1536,
                    "algorithm": Algorithm.FLAT.value,
                    "distance_metric": Distance.cosine.value,
                },
            },
            # //TODO: Add HSNW Vector Field
        ]
        super().__init__(index=index.__dict__, fields=fields)
