from dataclasses import dataclass
from typing import Optional


@dataclass
class Media:
    id: str
    original_prompt: Optional[str] = None
    revised_prompt: Optional[str] = None


@dataclass
class Video(Media):
    url: str  # Remote location for file
    eta: Optional[str] = None
    length: Optional[str] = None


@dataclass
class Image(Media):
    url: str  # Remote location for file
    alt_text: Optional[str] = None


@dataclass
class Audio(Media):
    url: Optional[str] = None  # Remote location for file
    base64_audio: Optional[str] = None  # Base64-encoded audio data
    length: Optional[str] = None

    def __post_init__(self):
        """Ensure that either `url` or `base64_audio` is provided, but not both."""

        if self.url and self.base64_audio:
            raise ValueError("Provide either `url` or `base64_audio`, not both.")
        if not self.url and not self.base64_audio:
            raise ValueError("Either `url` or `base64_audio` must be provided.")
