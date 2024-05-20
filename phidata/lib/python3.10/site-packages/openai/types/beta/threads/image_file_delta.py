# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from typing import Optional

from ...._models import BaseModel

__all__ = ["ImageFileDelta"]


class ImageFileDelta(BaseModel):
    file_id: Optional[str] = None
    """
    The [File](https://platform.openai.com/docs/api-reference/files) ID of the image
    in the message content.
    """
