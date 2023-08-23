from typing import Dict, Any

from pydantic import BaseModel


class Ivfflat(BaseModel):
    lists: int = 100
    probes: int = 10
    dynamic_lists: bool = True
    configuration: Dict[str, Any] = {
        "maintenance_work_mem": "2GB",
    }


class HNSW(BaseModel):
    m: int = 16
    ef: int = 50
    ef_construction: int = 200
    configuration: Dict[str, Any] = {
        "maintenance_work_mem": "2GB",
    }
