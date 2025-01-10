# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from typing_extensions import Literal

from ...._models import BaseModel

__all__ = ["ConversationItemInputAudioTranscriptionCompletedEvent"]


class ConversationItemInputAudioTranscriptionCompletedEvent(BaseModel):
    content_index: int
    """The index of the content part containing the audio."""

    event_id: str
    """The unique ID of the server event."""

    item_id: str
    """The ID of the user message item containing the audio."""

    transcript: str
    """The transcribed text."""

    type: Literal["conversation.item.input_audio_transcription.completed"]
    """
    The event type, must be `conversation.item.input_audio_transcription.completed`.
    """
