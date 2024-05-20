# File generated from our OpenAPI spec by Stainless.

from __future__ import annotations

from ..._compat import cached_property
from ..._resource import SyncAPIResource, AsyncAPIResource
from .translations import (
    Translations,
    AsyncTranslations,
    TranslationsWithRawResponse,
    AsyncTranslationsWithRawResponse,
    TranslationsWithStreamingResponse,
    AsyncTranslationsWithStreamingResponse,
)
from .transcriptions import (
    Transcriptions,
    AsyncTranscriptions,
    TranscriptionsWithRawResponse,
    AsyncTranscriptionsWithRawResponse,
    TranscriptionsWithStreamingResponse,
    AsyncTranscriptionsWithStreamingResponse,
)

__all__ = ["Audio", "AsyncAudio"]


class Audio(SyncAPIResource):
    @cached_property
    def transcriptions(self) -> Transcriptions:
        return Transcriptions(self._client)

    @cached_property
    def translations(self) -> Translations:
        return Translations(self._client)

    @cached_property
    def with_raw_response(self) -> AudioWithRawResponse:
        return AudioWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> AudioWithStreamingResponse:
        return AudioWithStreamingResponse(self)


class AsyncAudio(AsyncAPIResource):
    @cached_property
    def transcriptions(self) -> AsyncTranscriptions:
        return AsyncTranscriptions(self._client)

    @cached_property
    def translations(self) -> AsyncTranslations:
        return AsyncTranslations(self._client)

    @cached_property
    def with_raw_response(self) -> AsyncAudioWithRawResponse:
        return AsyncAudioWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> AsyncAudioWithStreamingResponse:
        return AsyncAudioWithStreamingResponse(self)


class AudioWithRawResponse:
    def __init__(self, audio: Audio) -> None:
        self._audio = audio

    @cached_property
    def transcriptions(self) -> TranscriptionsWithRawResponse:
        return TranscriptionsWithRawResponse(self._audio.transcriptions)

    @cached_property
    def translations(self) -> TranslationsWithRawResponse:
        return TranslationsWithRawResponse(self._audio.translations)


class AsyncAudioWithRawResponse:
    def __init__(self, audio: AsyncAudio) -> None:
        self._audio = audio

    @cached_property
    def transcriptions(self) -> AsyncTranscriptionsWithRawResponse:
        return AsyncTranscriptionsWithRawResponse(self._audio.transcriptions)

    @cached_property
    def translations(self) -> AsyncTranslationsWithRawResponse:
        return AsyncTranslationsWithRawResponse(self._audio.translations)


class AudioWithStreamingResponse:
    def __init__(self, audio: Audio) -> None:
        self._audio = audio

    @cached_property
    def transcriptions(self) -> TranscriptionsWithStreamingResponse:
        return TranscriptionsWithStreamingResponse(self._audio.transcriptions)

    @cached_property
    def translations(self) -> TranslationsWithStreamingResponse:
        return TranslationsWithStreamingResponse(self._audio.translations)


class AsyncAudioWithStreamingResponse:
    def __init__(self, audio: AsyncAudio) -> None:
        self._audio = audio

    @cached_property
    def transcriptions(self) -> AsyncTranscriptionsWithStreamingResponse:
        return AsyncTranscriptionsWithStreamingResponse(self._audio.transcriptions)

    @cached_property
    def translations(self) -> AsyncTranslationsWithStreamingResponse:
        return AsyncTranslationsWithStreamingResponse(self._audio.translations)
