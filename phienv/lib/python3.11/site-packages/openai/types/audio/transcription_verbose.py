# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from typing import List, Optional

from ..._models import BaseModel
from .transcription_word import TranscriptionWord
from .transcription_segment import TranscriptionSegment

__all__ = ["TranscriptionVerbose"]


class TranscriptionVerbose(BaseModel):
    duration: str
    """The duration of the input audio."""

    language: str
    """The language of the input audio."""

    text: str
    """The transcribed text."""

    segments: Optional[List[TranscriptionSegment]] = None
    """Segments of the transcribed text and their corresponding details."""

    words: Optional[List[TranscriptionWord]] = None
    """Extracted words and their corresponding timestamps."""
