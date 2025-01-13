# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from typing import Union
from typing_extensions import Annotated, TypeAlias

from ...._utils import PropertyInfo
from .error_event import ErrorEvent
from .response_done_event import ResponseDoneEvent
from .session_created_event import SessionCreatedEvent
from .session_updated_event import SessionUpdatedEvent
from .response_created_event import ResponseCreatedEvent
from .response_text_done_event import ResponseTextDoneEvent
from .rate_limits_updated_event import RateLimitsUpdatedEvent
from .response_audio_done_event import ResponseAudioDoneEvent
from .response_text_delta_event import ResponseTextDeltaEvent
from .conversation_created_event import ConversationCreatedEvent
from .response_audio_delta_event import ResponseAudioDeltaEvent
from .conversation_item_created_event import ConversationItemCreatedEvent
from .conversation_item_deleted_event import ConversationItemDeletedEvent
from .response_output_item_done_event import ResponseOutputItemDoneEvent
from .input_audio_buffer_cleared_event import InputAudioBufferClearedEvent
from .response_content_part_done_event import ResponseContentPartDoneEvent
from .response_output_item_added_event import ResponseOutputItemAddedEvent
from .conversation_item_truncated_event import ConversationItemTruncatedEvent
from .response_content_part_added_event import ResponseContentPartAddedEvent
from .input_audio_buffer_committed_event import InputAudioBufferCommittedEvent
from .response_audio_transcript_done_event import ResponseAudioTranscriptDoneEvent
from .response_audio_transcript_delta_event import ResponseAudioTranscriptDeltaEvent
from .input_audio_buffer_speech_started_event import InputAudioBufferSpeechStartedEvent
from .input_audio_buffer_speech_stopped_event import InputAudioBufferSpeechStoppedEvent
from .response_function_call_arguments_done_event import ResponseFunctionCallArgumentsDoneEvent
from .response_function_call_arguments_delta_event import ResponseFunctionCallArgumentsDeltaEvent
from .conversation_item_input_audio_transcription_failed_event import ConversationItemInputAudioTranscriptionFailedEvent
from .conversation_item_input_audio_transcription_completed_event import (
    ConversationItemInputAudioTranscriptionCompletedEvent,
)

__all__ = ["RealtimeServerEvent"]

RealtimeServerEvent: TypeAlias = Annotated[
    Union[
        ErrorEvent,
        SessionCreatedEvent,
        SessionUpdatedEvent,
        ConversationCreatedEvent,
        InputAudioBufferCommittedEvent,
        InputAudioBufferClearedEvent,
        InputAudioBufferSpeechStartedEvent,
        InputAudioBufferSpeechStoppedEvent,
        ConversationItemCreatedEvent,
        ConversationItemInputAudioTranscriptionCompletedEvent,
        ConversationItemInputAudioTranscriptionFailedEvent,
        ConversationItemTruncatedEvent,
        ConversationItemDeletedEvent,
        ResponseCreatedEvent,
        ResponseDoneEvent,
        ResponseOutputItemAddedEvent,
        ResponseOutputItemDoneEvent,
        ResponseContentPartAddedEvent,
        ResponseContentPartDoneEvent,
        ResponseTextDeltaEvent,
        ResponseTextDoneEvent,
        ResponseAudioTranscriptDeltaEvent,
        ResponseAudioTranscriptDoneEvent,
        ResponseAudioDeltaEvent,
        ResponseAudioDoneEvent,
        ResponseFunctionCallArgumentsDeltaEvent,
        ResponseFunctionCallArgumentsDoneEvent,
        RateLimitsUpdatedEvent,
    ],
    PropertyInfo(discriminator="type"),
]
