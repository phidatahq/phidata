# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from ...._models import BaseModel

__all__ = ["ImageFile"]


class ImageFile(BaseModel):
    file_id: str
    """
    The [File](https://platform.openai.com/docs/api-reference/files) ID of the image
    in the message content.
    """
