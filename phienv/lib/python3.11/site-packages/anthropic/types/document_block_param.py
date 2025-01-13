# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import Optional
from typing_extensions import Literal, Required, TypedDict

from .base64_pdf_source_param import Base64PDFSourceParam
from .cache_control_ephemeral_param import CacheControlEphemeralParam

__all__ = ["DocumentBlockParam"]


class DocumentBlockParam(TypedDict, total=False):
    source: Required[Base64PDFSourceParam]

    type: Required[Literal["document"]]

    cache_control: Optional[CacheControlEphemeralParam]
