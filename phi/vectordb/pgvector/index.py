from pydantic import BaseModel


class Ivfflat(BaseModel):
    distance_metric: str = "cosine"
    nlist: int = 100
    dynamic_list: bool = True
    probes: int = 10


class HNSW(BaseModel):
    distance_metric: str = "cosine"
    ef_construction: int = 200
    ef: int = 50
    m: int = 16
