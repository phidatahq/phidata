from typing import Any, List

from pydantic import BaseModel

from phi.document.base import Document


class Reader(BaseModel):
    chunk: bool = True
    chunk_size: int = 3000
    separators: List[str] = ["\n", "\n\n", "\r", "\r\n", "\n\r", "\t", " ", "  "]

    def read(self, obj: Any) -> List[Document]:
        raise NotImplementedError

    def clean_text(self, text: str) -> str:
        """Clean the text by replacing multiple newlines with a single newline"""
        import re

        # Replace multiple newlines with a single newline
        cleaned_text = re.sub(r"\n+", "\n", text)
        # Replace multiple spaces with a single space
        cleaned_text = re.sub(r"\s+", " ", cleaned_text)
        # Replace multiple tabs with a single tab
        cleaned_text = re.sub(r"\t+", "\t", cleaned_text)
        # Replace multiple carriage returns with a single carriage return
        cleaned_text = re.sub(r"\r+", "\r", cleaned_text)
        # Replace multiple form feeds with a single form feed
        cleaned_text = re.sub(r"\f+", "\f", cleaned_text)
        # Replace multiple vertical tabs with a single vertical tab
        cleaned_text = re.sub(r"\v+", "\v", cleaned_text)

        return cleaned_text

    def chunk_document(self, document: Document) -> List[Document]:
        """Chunk the document content into smaller documents"""
        content = document.content
        cleaned_content = self.clean_text(content)
        content_length = len(cleaned_content)
        chunked_documents: List[Document] = []
        chunk_number = 1
        chunk_meta_data = document.meta_data

        start = 0
        while start < content_length:
            end = start + self.chunk_size

            # Ensure we're not splitting a word in half
            if end < content_length:
                while end > start and cleaned_content[end] not in [" ", "\n", "\r", "\t"]:
                    end -= 1

            # If the entire chunk is a word, then just split it at self.chunk_size
            if end == start:
                end = start + self.chunk_size

            # If the end is greater than the content length, then set it to the content length
            if end > content_length:
                end = content_length

            chunk = cleaned_content[start:end]
            meta_data = chunk_meta_data.copy()
            meta_data["chunk"] = chunk_number
            chunk_id = None
            if document.id:
                chunk_id = f"{document.id}_{chunk_number}"
            elif document.name:
                chunk_id = f"{document.name}_{chunk_number}"
            meta_data["chunk_size"] = len(chunk)
            chunked_documents.append(
                Document(
                    id=chunk_id,
                    name=document.name,
                    meta_data=meta_data,
                    content=chunk,
                )
            )
            chunk_number += 1
            start = end
        return chunked_documents
