# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import List, Union, Iterable
from typing_extensions import Literal

import httpx

from .... import _legacy_response
from ...._types import NOT_GIVEN, Body, Query, Headers, NotGiven
from ...._utils import (
    maybe_transform,
    async_maybe_transform,
)
from ...._compat import cached_property
from ...._resource import SyncAPIResource, AsyncAPIResource
from ...._response import to_streamed_response_wrapper, async_to_streamed_response_wrapper
from ...._base_client import make_request_options
from ....types.beta.realtime import session_create_params
from ....types.beta.realtime.session_create_response import SessionCreateResponse

__all__ = ["Sessions", "AsyncSessions"]


class Sessions(SyncAPIResource):
    @cached_property
    def with_raw_response(self) -> SessionsWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return the
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/openai/openai-python#accessing-raw-response-data-eg-headers
        """
        return SessionsWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> SessionsWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/openai/openai-python#with_streaming_response
        """
        return SessionsWithStreamingResponse(self)

    def create(
        self,
        *,
        model: Literal[
            "gpt-4o-realtime-preview",
            "gpt-4o-realtime-preview-2024-10-01",
            "gpt-4o-realtime-preview-2024-12-17",
            "gpt-4o-mini-realtime-preview",
            "gpt-4o-mini-realtime-preview-2024-12-17",
        ],
        input_audio_format: Literal["pcm16", "g711_ulaw", "g711_alaw"] | NotGiven = NOT_GIVEN,
        input_audio_transcription: session_create_params.InputAudioTranscription | NotGiven = NOT_GIVEN,
        instructions: str | NotGiven = NOT_GIVEN,
        max_response_output_tokens: Union[int, Literal["inf"]] | NotGiven = NOT_GIVEN,
        modalities: List[Literal["text", "audio"]] | NotGiven = NOT_GIVEN,
        output_audio_format: Literal["pcm16", "g711_ulaw", "g711_alaw"] | NotGiven = NOT_GIVEN,
        temperature: float | NotGiven = NOT_GIVEN,
        tool_choice: str | NotGiven = NOT_GIVEN,
        tools: Iterable[session_create_params.Tool] | NotGiven = NOT_GIVEN,
        turn_detection: session_create_params.TurnDetection | NotGiven = NOT_GIVEN,
        voice: Literal["alloy", "ash", "ballad", "coral", "echo", "sage", "shimmer", "verse"] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> SessionCreateResponse:
        """
        Create an ephemeral API token for use in client-side applications with the
        Realtime API. Can be configured with the same session parameters as the
        `session.update` client event.

        It responds with a session object, plus a `client_secret` key which contains a
        usable ephemeral API token that can be used to authenticate browser clients for
        the Realtime API.

        Args:
          model: The Realtime model used for this session.

          input_audio_format: The format of input audio. Options are `pcm16`, `g711_ulaw`, or `g711_alaw`.

          input_audio_transcription: Configuration for input audio transcription, defaults to off and can be set to
              `null` to turn off once on. Input audio transcription is not native to the
              model, since the model consumes audio directly. Transcription runs
              asynchronously through Whisper and should be treated as rough guidance rather
              than the representation understood by the model.

          instructions: The default system instructions (i.e. system message) prepended to model calls.
              This field allows the client to guide the model on desired responses. The model
              can be instructed on response content and format, (e.g. "be extremely succinct",
              "act friendly", "here are examples of good responses") and on audio behavior
              (e.g. "talk quickly", "inject emotion into your voice", "laugh frequently"). The
              instructions are not guaranteed to be followed by the model, but they provide
              guidance to the model on the desired behavior.

              Note that the server sets default instructions which will be used if this field
              is not set and are visible in the `session.created` event at the start of the
              session.

          max_response_output_tokens: Maximum number of output tokens for a single assistant response, inclusive of
              tool calls. Provide an integer between 1 and 4096 to limit output tokens, or
              `inf` for the maximum available tokens for a given model. Defaults to `inf`.

          modalities: The set of modalities the model can respond with. To disable audio, set this to
              ["text"].

          output_audio_format: The format of output audio. Options are `pcm16`, `g711_ulaw`, or `g711_alaw`.

          temperature: Sampling temperature for the model, limited to [0.6, 1.2]. Defaults to 0.8.

          tool_choice: How the model chooses tools. Options are `auto`, `none`, `required`, or specify
              a function.

          tools: Tools (functions) available to the model.

          turn_detection: Configuration for turn detection. Can be set to `null` to turn off. Server VAD
              means that the model will detect the start and end of speech based on audio
              volume and respond at the end of user speech.

          voice: The voice the model uses to respond. Voice cannot be changed during the session
              once the model has responded with audio at least once. Current voice options are
              `alloy`, `ash`, `ballad`, `coral`, `echo` `sage`, `shimmer` and `verse`.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        extra_headers = {"OpenAI-Beta": "assistants=v2", **(extra_headers or {})}
        return self._post(
            "/realtime/sessions",
            body=maybe_transform(
                {
                    "model": model,
                    "input_audio_format": input_audio_format,
                    "input_audio_transcription": input_audio_transcription,
                    "instructions": instructions,
                    "max_response_output_tokens": max_response_output_tokens,
                    "modalities": modalities,
                    "output_audio_format": output_audio_format,
                    "temperature": temperature,
                    "tool_choice": tool_choice,
                    "tools": tools,
                    "turn_detection": turn_detection,
                    "voice": voice,
                },
                session_create_params.SessionCreateParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=SessionCreateResponse,
        )


class AsyncSessions(AsyncAPIResource):
    @cached_property
    def with_raw_response(self) -> AsyncSessionsWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return the
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/openai/openai-python#accessing-raw-response-data-eg-headers
        """
        return AsyncSessionsWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> AsyncSessionsWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/openai/openai-python#with_streaming_response
        """
        return AsyncSessionsWithStreamingResponse(self)

    async def create(
        self,
        *,
        model: Literal[
            "gpt-4o-realtime-preview",
            "gpt-4o-realtime-preview-2024-10-01",
            "gpt-4o-realtime-preview-2024-12-17",
            "gpt-4o-mini-realtime-preview",
            "gpt-4o-mini-realtime-preview-2024-12-17",
        ],
        input_audio_format: Literal["pcm16", "g711_ulaw", "g711_alaw"] | NotGiven = NOT_GIVEN,
        input_audio_transcription: session_create_params.InputAudioTranscription | NotGiven = NOT_GIVEN,
        instructions: str | NotGiven = NOT_GIVEN,
        max_response_output_tokens: Union[int, Literal["inf"]] | NotGiven = NOT_GIVEN,
        modalities: List[Literal["text", "audio"]] | NotGiven = NOT_GIVEN,
        output_audio_format: Literal["pcm16", "g711_ulaw", "g711_alaw"] | NotGiven = NOT_GIVEN,
        temperature: float | NotGiven = NOT_GIVEN,
        tool_choice: str | NotGiven = NOT_GIVEN,
        tools: Iterable[session_create_params.Tool] | NotGiven = NOT_GIVEN,
        turn_detection: session_create_params.TurnDetection | NotGiven = NOT_GIVEN,
        voice: Literal["alloy", "ash", "ballad", "coral", "echo", "sage", "shimmer", "verse"] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> SessionCreateResponse:
        """
        Create an ephemeral API token for use in client-side applications with the
        Realtime API. Can be configured with the same session parameters as the
        `session.update` client event.

        It responds with a session object, plus a `client_secret` key which contains a
        usable ephemeral API token that can be used to authenticate browser clients for
        the Realtime API.

        Args:
          model: The Realtime model used for this session.

          input_audio_format: The format of input audio. Options are `pcm16`, `g711_ulaw`, or `g711_alaw`.

          input_audio_transcription: Configuration for input audio transcription, defaults to off and can be set to
              `null` to turn off once on. Input audio transcription is not native to the
              model, since the model consumes audio directly. Transcription runs
              asynchronously through Whisper and should be treated as rough guidance rather
              than the representation understood by the model.

          instructions: The default system instructions (i.e. system message) prepended to model calls.
              This field allows the client to guide the model on desired responses. The model
              can be instructed on response content and format, (e.g. "be extremely succinct",
              "act friendly", "here are examples of good responses") and on audio behavior
              (e.g. "talk quickly", "inject emotion into your voice", "laugh frequently"). The
              instructions are not guaranteed to be followed by the model, but they provide
              guidance to the model on the desired behavior.

              Note that the server sets default instructions which will be used if this field
              is not set and are visible in the `session.created` event at the start of the
              session.

          max_response_output_tokens: Maximum number of output tokens for a single assistant response, inclusive of
              tool calls. Provide an integer between 1 and 4096 to limit output tokens, or
              `inf` for the maximum available tokens for a given model. Defaults to `inf`.

          modalities: The set of modalities the model can respond with. To disable audio, set this to
              ["text"].

          output_audio_format: The format of output audio. Options are `pcm16`, `g711_ulaw`, or `g711_alaw`.

          temperature: Sampling temperature for the model, limited to [0.6, 1.2]. Defaults to 0.8.

          tool_choice: How the model chooses tools. Options are `auto`, `none`, `required`, or specify
              a function.

          tools: Tools (functions) available to the model.

          turn_detection: Configuration for turn detection. Can be set to `null` to turn off. Server VAD
              means that the model will detect the start and end of speech based on audio
              volume and respond at the end of user speech.

          voice: The voice the model uses to respond. Voice cannot be changed during the session
              once the model has responded with audio at least once. Current voice options are
              `alloy`, `ash`, `ballad`, `coral`, `echo` `sage`, `shimmer` and `verse`.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        extra_headers = {"OpenAI-Beta": "assistants=v2", **(extra_headers or {})}
        return await self._post(
            "/realtime/sessions",
            body=await async_maybe_transform(
                {
                    "model": model,
                    "input_audio_format": input_audio_format,
                    "input_audio_transcription": input_audio_transcription,
                    "instructions": instructions,
                    "max_response_output_tokens": max_response_output_tokens,
                    "modalities": modalities,
                    "output_audio_format": output_audio_format,
                    "temperature": temperature,
                    "tool_choice": tool_choice,
                    "tools": tools,
                    "turn_detection": turn_detection,
                    "voice": voice,
                },
                session_create_params.SessionCreateParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=SessionCreateResponse,
        )


class SessionsWithRawResponse:
    def __init__(self, sessions: Sessions) -> None:
        self._sessions = sessions

        self.create = _legacy_response.to_raw_response_wrapper(
            sessions.create,
        )


class AsyncSessionsWithRawResponse:
    def __init__(self, sessions: AsyncSessions) -> None:
        self._sessions = sessions

        self.create = _legacy_response.async_to_raw_response_wrapper(
            sessions.create,
        )


class SessionsWithStreamingResponse:
    def __init__(self, sessions: Sessions) -> None:
        self._sessions = sessions

        self.create = to_streamed_response_wrapper(
            sessions.create,
        )


class AsyncSessionsWithStreamingResponse:
    def __init__(self, sessions: AsyncSessions) -> None:
        self._sessions = sessions

        self.create = async_to_streamed_response_wrapper(
            sessions.create,
        )
