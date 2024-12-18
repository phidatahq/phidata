from typing import Optional, Any

from pydantic import BaseModel, model_validator


class Media(BaseModel):
    id: str
    original_prompt: Optional[str] = None
    revised_prompt: Optional[str] = None


class Video(Media):
    url: str  # Remote location for file
    eta: Optional[str] = None
    length: Optional[str] = None


class Image(Media):
    url: str  # Remote location for file
    alt_text: Optional[str] = None


class Audio(Media):
    url: Optional[str] = None  # Remote location for file
    base64_audio: Optional[str] = None  # Base64-encoded audio data
    length: Optional[str] = None

    @model_validator(mode="before")
    def validate_exclusive_audio(cls, data: Any):
        """
        Ensure that either `url` or `base64_audio` is provided, but not both.
        """
        if data.get("url") and data.get("base64_audio"):
            raise ValueError("Provide either `url` or `base64_audio`, not both.")
        if not data.get("url") and not data.get("base64_audio"):
            raise ValueError("Either `url` or `base64_audio` must be provided.")
        return data
