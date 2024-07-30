from typing import List, Optional, Callable, Any

from phi.document import Document
from phi.knowledge.base import AssistantKnowledge
from phi.utils.log import logger


class LangChainKnowledgeBase(AssistantKnowledge):
    loader: Optional[Callable] = None

    vectorstore: Optional[Any] = None
    search_kwargs: Optional[dict] = None

    retriever: Optional[Any] = None

    def search(self, query: str, num_documents: Optional[int] = None) -> List[Document]:
        """Returns relevant documents matching the query"""

        try:
            from langchain_core.vectorstores import VectorStoreRetriever
            from langchain_core.documents import Document as LangChainDocument
        except ImportError:
            raise ImportError(
                "The `langchain` package is not installed. Please install it via `pip install langchain`."
            )

        if self.vectorstore is not None and self.retriever is None:
            logger.debug("Creating retriever")
            if self.search_kwargs is None:
                self.search_kwargs = {"k": self.num_documents}
            self.retriever = self.vectorstore.as_retriever(search_kwargs=self.search_kwargs)

        if self.retriever is None:
            logger.error("No retriever provided")
            return []

        if not isinstance(self.retriever, VectorStoreRetriever):
            raise ValueError(f"Retriever is not of type VectorStoreRetriever: {self.retriever}")

        _num_documents = num_documents or self.num_documents
        logger.debug(f"Getting {_num_documents} relevant documents for query: {query}")
        lc_documents: List[LangChainDocument] = self.retriever.invoke(input=query)
        documents = []
        for lc_doc in lc_documents:
            documents.append(
                Document(
                    content=lc_doc.page_content,
                    meta_data=lc_doc.metadata,
                )
            )
        return documents

    def load(self, recreate: bool = False, upsert: bool = True, skip_existing: bool = True) -> None:
        if self.loader is None:
            logger.error("No loader provided for LangChainKnowledgeBase")
            return
        self.loader()

    def exists(self) -> bool:
        logger.warning("LangChainKnowledgeBase.exists() not supported - please check the vectorstore manually.")
        return True
