from typing import List, Iterator

from pydantic import BaseModel, ConfigDict

from phi.document import Document


class LLMKnowledgeBase(BaseModel):
    """Base class for LLM knowledge base"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @property
    def document_lists(self) -> Iterator[List[Document]]:
        """Iterate over document lists in the knowledge base"""
        raise NotImplementedError

    def search(self, query: str) -> List[Document]:
        """Return all relevant documents matching the query"""
        raise NotImplementedError

    def load(self, recreate: bool = False) -> None:
        """Load the knowledge base to vector db"""
        raise NotImplementedError
