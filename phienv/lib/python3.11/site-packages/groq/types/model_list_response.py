# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from typing import List
from typing_extensions import Literal

from .model import Model
from .._models import BaseModel

__all__ = ["ModelListResponse"]


class ModelListResponse(BaseModel):
    data: List[Model]

    object: Literal["list"]
