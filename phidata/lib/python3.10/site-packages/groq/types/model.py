# File generated from our OpenAPI spec by Stainless.

from typing import Optional

from .._models import BaseModel

__all__ = ["Model"]


class Model(BaseModel):
    id: Optional[str] = None

    created: Optional[int] = None

    object: Optional[str] = None

    owned_by: Optional[str] = None
