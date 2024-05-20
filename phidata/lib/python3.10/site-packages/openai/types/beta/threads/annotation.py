# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from typing import Union
from typing_extensions import Annotated

from ...._utils import PropertyInfo
from .file_path_annotation import FilePathAnnotation
from .file_citation_annotation import FileCitationAnnotation

__all__ = ["Annotation"]

Annotation = Annotated[Union[FileCitationAnnotation, FilePathAnnotation], PropertyInfo(discriminator="type")]
