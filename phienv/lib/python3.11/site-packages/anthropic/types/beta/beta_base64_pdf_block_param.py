# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import Optional
from typing_extensions import Literal, Required, TypedDict

from .beta_base64_pdf_source_param import BetaBase64PDFSourceParam
from .beta_cache_control_ephemeral_param import BetaCacheControlEphemeralParam

__all__ = ["BetaBase64PDFBlockParam"]


class BetaBase64PDFBlockParam(TypedDict, total=False):
    source: Required[BetaBase64PDFSourceParam]

    type: Required[Literal["document"]]

    cache_control: Optional[BetaCacheControlEphemeralParam]
