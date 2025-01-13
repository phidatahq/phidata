# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import List, Union, Mapping, cast
from typing_extensions import Literal

import httpx

from ..._types import NOT_GIVEN, Body, Query, Headers, NotGiven, FileTypes
from ..._utils import (
    extract_files,
    maybe_transform,
    deepcopy_minimal,
    async_maybe_transform,
)
from ..._compat import cached_property
from ..._resource import SyncAPIResource, AsyncAPIResource
from ..._response import (
    to_raw_response_wrapper,
    to_streamed_response_wrapper,
    async_to_raw_response_wrapper,
    async_to_streamed_response_wrapper,
)
from ...types.audio import transcription_create_params
from ..._base_client import make_request_options
from ...types.audio.transcription import Transcription

__all__ = ["Transcriptions", "AsyncTranscriptions"]


class Transcriptions(SyncAPIResource):
    @cached_property
    def with_raw_response(self) -> TranscriptionsWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return the
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/groq/groq-python#accessing-raw-response-data-eg-headers
        """
        return TranscriptionsWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> TranscriptionsWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/groq/groq-python#with_streaming_response
        """
        return TranscriptionsWithStreamingResponse(self)

    def create(
        self,
        *,
        file: FileTypes,
        model: Union[str, Literal["whisper-large-v3"]],
        language: Union[
            str,
            Literal[
                "en",
                "zh",
                "de",
                "es",
                "ru",
                "ko",
                "fr",
                "ja",
                "pt",
                "tr",
                "pl",
                "ca",
                "nl",
                "ar",
                "sv",
                "it",
                "id",
                "hi",
                "fi",
                "vi",
                "he",
                "uk",
                "el",
                "ms",
                "cs",
                "ro",
                "da",
                "hu",
                "ta",
                "no",
                "th",
                "ur",
                "hr",
                "bg",
                "lt",
                "la",
                "mi",
                "ml",
                "cy",
                "sk",
                "te",
                "fa",
                "lv",
                "bn",
                "sr",
                "az",
                "sl",
                "kn",
                "et",
                "mk",
                "br",
                "eu",
                "is",
                "hy",
                "ne",
                "mn",
                "bs",
                "kk",
                "sq",
                "sw",
                "gl",
                "mr",
                "pa",
                "si",
                "km",
                "sn",
                "yo",
                "so",
                "af",
                "oc",
                "ka",
                "be",
                "tg",
                "sd",
                "gu",
                "am",
                "yi",
                "lo",
                "uz",
                "fo",
                "ht",
                "ps",
                "tk",
                "nn",
                "mt",
                "sa",
                "lb",
                "my",
                "bo",
                "tl",
                "mg",
                "as",
                "tt",
                "haw",
                "ln",
                "ha",
                "ba",
                "jv",
                "su",
                "yue",
            ],
        ]
        | NotGiven = NOT_GIVEN,
        prompt: str | NotGiven = NOT_GIVEN,
        response_format: Literal["json", "text", "verbose_json"] | NotGiven = NOT_GIVEN,
        temperature: float | NotGiven = NOT_GIVEN,
        timestamp_granularities: List[Literal["word", "segment"]] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Transcription:
        """
        Transcribes audio into the input language.

        Args:
          file:
              The audio file object (not file name) to transcribe, in one of these formats:
              flac, mp3, mp4, mpeg, mpga, m4a, ogg, wav, or webm.

          model: ID of the model to use. Only `whisper-large-v3` is currently available.

          language: The language of the input audio. Supplying the input language in
              [ISO-639-1](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes) format will
              improve accuracy and latency.

          prompt: An optional text to guide the model's style or continue a previous audio
              segment. The [prompt](/docs/speech-text) should match the audio language.

          response_format: The format of the transcript output, in one of these options: `json`, `text`, or
              `verbose_json`.

          temperature: The sampling temperature, between 0 and 1. Higher values like 0.8 will make the
              output more random, while lower values like 0.2 will make it more focused and
              deterministic. If set to 0, the model will use
              [log probability](https://en.wikipedia.org/wiki/Log_probability) to
              automatically increase the temperature until certain thresholds are hit.

          timestamp_granularities: The timestamp granularities to populate for this transcription.
              `response_format` must be set `verbose_json` to use timestamp granularities.
              Either or both of these options are supported: `word`, or `segment`. Note: There
              is no additional latency for segment timestamps, but generating word timestamps
              incurs additional latency.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        body = deepcopy_minimal(
            {
                "file": file,
                "model": model,
                "language": language,
                "prompt": prompt,
                "response_format": response_format,
                "temperature": temperature,
                "timestamp_granularities": timestamp_granularities,
            }
        )
        files = extract_files(cast(Mapping[str, object], body), paths=[["file"]])
        # It should be noted that the actual Content-Type header that will be
        # sent to the server will contain a `boundary` parameter, e.g.
        # multipart/form-data; boundary=---abc--
        extra_headers = {"Content-Type": "multipart/form-data", **(extra_headers or {})}
        return self._post(
            "/openai/v1/audio/transcriptions",
            body=maybe_transform(body, transcription_create_params.TranscriptionCreateParams),
            files=files,
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=Transcription,
        )


class AsyncTranscriptions(AsyncAPIResource):
    @cached_property
    def with_raw_response(self) -> AsyncTranscriptionsWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return the
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/groq/groq-python#accessing-raw-response-data-eg-headers
        """
        return AsyncTranscriptionsWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> AsyncTranscriptionsWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/groq/groq-python#with_streaming_response
        """
        return AsyncTranscriptionsWithStreamingResponse(self)

    async def create(
        self,
        *,
        file: FileTypes,
        model: Union[str, Literal["whisper-large-v3"]],
        language: Union[
            str,
            Literal[
                "en",
                "zh",
                "de",
                "es",
                "ru",
                "ko",
                "fr",
                "ja",
                "pt",
                "tr",
                "pl",
                "ca",
                "nl",
                "ar",
                "sv",
                "it",
                "id",
                "hi",
                "fi",
                "vi",
                "he",
                "uk",
                "el",
                "ms",
                "cs",
                "ro",
                "da",
                "hu",
                "ta",
                "no",
                "th",
                "ur",
                "hr",
                "bg",
                "lt",
                "la",
                "mi",
                "ml",
                "cy",
                "sk",
                "te",
                "fa",
                "lv",
                "bn",
                "sr",
                "az",
                "sl",
                "kn",
                "et",
                "mk",
                "br",
                "eu",
                "is",
                "hy",
                "ne",
                "mn",
                "bs",
                "kk",
                "sq",
                "sw",
                "gl",
                "mr",
                "pa",
                "si",
                "km",
                "sn",
                "yo",
                "so",
                "af",
                "oc",
                "ka",
                "be",
                "tg",
                "sd",
                "gu",
                "am",
                "yi",
                "lo",
                "uz",
                "fo",
                "ht",
                "ps",
                "tk",
                "nn",
                "mt",
                "sa",
                "lb",
                "my",
                "bo",
                "tl",
                "mg",
                "as",
                "tt",
                "haw",
                "ln",
                "ha",
                "ba",
                "jv",
                "su",
                "yue",
            ],
        ]
        | NotGiven = NOT_GIVEN,
        prompt: str | NotGiven = NOT_GIVEN,
        response_format: Literal["json", "text", "verbose_json"] | NotGiven = NOT_GIVEN,
        temperature: float | NotGiven = NOT_GIVEN,
        timestamp_granularities: List[Literal["word", "segment"]] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Transcription:
        """
        Transcribes audio into the input language.

        Args:
          file:
              The audio file object (not file name) to transcribe, in one of these formats:
              flac, mp3, mp4, mpeg, mpga, m4a, ogg, wav, or webm.

          model: ID of the model to use. Only `whisper-large-v3` is currently available.

          language: The language of the input audio. Supplying the input language in
              [ISO-639-1](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes) format will
              improve accuracy and latency.

          prompt: An optional text to guide the model's style or continue a previous audio
              segment. The [prompt](/docs/speech-text) should match the audio language.

          response_format: The format of the transcript output, in one of these options: `json`, `text`, or
              `verbose_json`.

          temperature: The sampling temperature, between 0 and 1. Higher values like 0.8 will make the
              output more random, while lower values like 0.2 will make it more focused and
              deterministic. If set to 0, the model will use
              [log probability](https://en.wikipedia.org/wiki/Log_probability) to
              automatically increase the temperature until certain thresholds are hit.

          timestamp_granularities: The timestamp granularities to populate for this transcription.
              `response_format` must be set `verbose_json` to use timestamp granularities.
              Either or both of these options are supported: `word`, or `segment`. Note: There
              is no additional latency for segment timestamps, but generating word timestamps
              incurs additional latency.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        body = deepcopy_minimal(
            {
                "file": file,
                "model": model,
                "language": language,
                "prompt": prompt,
                "response_format": response_format,
                "temperature": temperature,
                "timestamp_granularities": timestamp_granularities,
            }
        )
        files = extract_files(cast(Mapping[str, object], body), paths=[["file"]])
        # It should be noted that the actual Content-Type header that will be
        # sent to the server will contain a `boundary` parameter, e.g.
        # multipart/form-data; boundary=---abc--
        extra_headers = {"Content-Type": "multipart/form-data", **(extra_headers or {})}
        return await self._post(
            "/openai/v1/audio/transcriptions",
            body=await async_maybe_transform(body, transcription_create_params.TranscriptionCreateParams),
            files=files,
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=Transcription,
        )


class TranscriptionsWithRawResponse:
    def __init__(self, transcriptions: Transcriptions) -> None:
        self._transcriptions = transcriptions

        self.create = to_raw_response_wrapper(
            transcriptions.create,
        )


class AsyncTranscriptionsWithRawResponse:
    def __init__(self, transcriptions: AsyncTranscriptions) -> None:
        self._transcriptions = transcriptions

        self.create = async_to_raw_response_wrapper(
            transcriptions.create,
        )


class TranscriptionsWithStreamingResponse:
    def __init__(self, transcriptions: Transcriptions) -> None:
        self._transcriptions = transcriptions

        self.create = to_streamed_response_wrapper(
            transcriptions.create,
        )


class AsyncTranscriptionsWithStreamingResponse:
    def __init__(self, transcriptions: AsyncTranscriptions) -> None:
        self._transcriptions = transcriptions

        self.create = async_to_streamed_response_wrapper(
            transcriptions.create,
        )
