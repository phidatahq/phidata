from typing import List

from phi.document.base import Document
from phi.document.reader.base import Reader
from phi.aws.resource.s3.object import S3Object
from phi.utils.log import logger


class S3PDFReader(Reader):
    """Reader for PDF files on S3"""

    def read(self, s3_object: S3Object) -> List[Document]:
        from io import BytesIO

        if not s3_object:
            raise ValueError("No s3_object provided")

        try:
            from pypdf import PdfReader as DocumentReader  # noqa: F401
        except ImportError:
            raise ImportError("`pypdf` not installed")

        try:
            logger.info(f"Reading: {s3_object.uri}")

            object_resource = s3_object.get_resource()
            object_body = object_resource.get()["Body"]
            doc_name = s3_object.name.split("/")[-1].split(".")[0].replace("/", "_").replace(" ", "_")
            doc_reader = DocumentReader(BytesIO(object_body.read()))
            documents = [
                Document(
                    name=doc_name,
                    id=f"{doc_name}_{page_number}",
                    meta_data={"page": page_number},
                    content=page.extract_text(),
                )
                for page_number, page in enumerate(doc_reader.pages, start=1)
            ]
            if self.chunk:
                chunked_documents = []
                for document in documents:
                    chunked_documents.extend(self.chunk_document(document))
                return chunked_documents
            return documents
        except Exception:
            raise
