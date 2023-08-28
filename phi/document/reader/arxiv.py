from typing import List

import arxiv
from phi.document.base import Document
from phi.document.reader.base import Reader


class ArxivReader(Reader):
    max_results: int = 5  # Top articles
    sort_by: arxiv.SortCriterion = arxiv.SortCriterion.Relevance

    def read(self, query: str) -> List[Document]:
        """
        search a query from arxiv's database

        This function gets the top_k articles based on a user's query, sorted by relevance from arxiv

        @param query:
        @return:
        """

        documents = []
        search = arxiv.Search(query=query, max_results=self.max_results, sort_by=self.sort_by)

        for result in search.results():
            links = ", ".join([x.href for x in result.links])

            documents.append(
                Document(
                    name=result.title,
                    meta_data={"pdf_url": str(result.pdf_url), "article_links": links},
                    content=result.summary,
                )
            )

        return documents
