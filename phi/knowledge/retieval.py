from pydantic import BaseModel


class RetrievalStrategy(BaseModel):
    num_documents: int = 2


class SemanticSearch(RetrievalStrategy):
    pass


class KeywordSearch(RetrievalStrategy):
    # Enables prefix matching i.e. match words that start with the query string
    prefix_match: bool = True


class HybridSearch(RetrievalStrategy):
    # Weight for vector score in hybrid search
    # Weight for text rank is 1 - vector_score_weight
    vector_score_weight: float = 0.5
    # Enables prefix matching i.e. match words that start with the query string
    prefix_match: bool = True
