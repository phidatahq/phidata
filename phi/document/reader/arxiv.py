from typing import List

import arxiv

from phi.document.base import Document
from phi.document.reader.base import Reader
from phi.document.reader.pdf import PDFReader
from pathlib import Path

class ArxivReader(Reader):
    max_results: int = 5  # Top articles
    # download_files: bool = True
    sort_by: arxiv.SortCriterion = arxiv.SortCriterion.Relevance
    # pdfreader: PDFReader = PDFReader()
    # filepath:str = "./tmp/arxiv_pdf/"

    def read(self, query: str) -> List[Document]:
        """
        search a query from arXiv's database

        This function gets the top_k articles based on a user's query, sorted by relevance from arxiv

        @param query:
        @return:
        """
        # Summarizing of one doc is logical
        # if self.download_files:
        #     self.max_results = 1

        documents = []
        search = arxiv.Search(
            query=query, max_results=self.max_results, sort_by=self.sort_by
        )

        for result in search.results():
            links = ", ".join([x.href for x in result.links])

            documents.append(
                Document(
                    name=result.title,
                    meta_data={"pdf_url": str( result.pdf_url), "article_links" : links},
                    content=result.summary,
                )
            )
            # # Download Files when need more detailed information
            # if self.download_files:
            #     returnresult = result.download_pdf(filename=f"{result.title}.pdf")
            #     _pdf_path: Path = Path(f"{result.title}.pdf")
            #     documents.extend(self.pdfreader.read(path=_pdf_path))
            #     if _pdf_path.exists():
            #         _pdf_path.unlink()

        return documents
