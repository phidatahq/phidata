from typing import List, Iterator, Optional

from phi.document import Document
from phi.aws.resource.s3.bucket import S3Bucket
from phi.aws.resource.s3.object import S3Object
from phi.document.reader.s3.pdf import S3PDFReader
from phi.knowledge.base import KnowledgeBase


class S3PDFKnowledgeBase(KnowledgeBase):
    key: Optional[str] = None
    bucket_name: Optional[str] = None
    bucket: Optional[S3Bucket] = None
    object: Optional[S3Object] = None
    reader: S3PDFReader = S3PDFReader()

    @property
    def document_lists(self) -> Iterator[List[Document]]:
        """Iterate over PDFs in a s3 bucket and yield lists of documents.
        Each object yielded by the iterator is a list of documents.

        Returns:
            Iterator[List[Document]]: Iterator yielding list of documents
        """

        s3_objects_to_read: List[S3Object] = []

        if self.bucket is None and self.bucket_name is None:
            raise ValueError("No bucket or bucket_name provided")

        if self.bucket is not None and self.bucket_name is not None:
            raise ValueError("Provide either bucket or bucket_name")

        if self.object is not None and self.key is not None:
            raise ValueError("Provide either object or key")

        if self.bucket_name is not None:
            self.bucket = S3Bucket(name=self.bucket_name)

        if self.bucket is not None:
            if self.key is not None:
                _object = S3Object(bucket_name=self.bucket.name, name=self.key)
                s3_objects_to_read.append(_object)
            elif self.object is not None:
                s3_objects_to_read.append(self.object)
            else:
                s3_objects_to_read.extend(self.bucket.get_objects())

        for s3_object in s3_objects_to_read:
            if s3_object.name.endswith(".pdf"):
                yield self.reader.read(s3_object=s3_object)
