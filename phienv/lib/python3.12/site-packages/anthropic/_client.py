# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

import os
from typing import Any, Union, Mapping
from typing_extensions import Self, override

import httpx

from . import _constants, _exceptions
from ._qs import Querystring
from ._types import (
    NOT_GIVEN,
    Omit,
    Headers,
    Timeout,
    NotGiven,
    Transport,
    ProxiesTypes,
    RequestOptions,
)
from ._utils import (
    is_given,
    get_async_library,
)
from ._version import __version__
from .resources import models, completions
from ._streaming import Stream as Stream, AsyncStream as AsyncStream
from ._exceptions import APIStatusError
from ._base_client import (
    DEFAULT_MAX_RETRIES,
    SyncAPIClient,
    AsyncAPIClient,
)
from .resources.beta import beta
from .resources.messages import messages

__all__ = [
    "Timeout",
    "Transport",
    "ProxiesTypes",
    "RequestOptions",
    "Anthropic",
    "AsyncAnthropic",
    "Client",
    "AsyncClient",
]


class Anthropic(SyncAPIClient):
    completions: completions.Completions
    messages: messages.Messages
    models: models.Models
    beta: beta.Beta
    with_raw_response: AnthropicWithRawResponse
    with_streaming_response: AnthropicWithStreamedResponse

    # client options
    api_key: str | None
    auth_token: str | None

    # constants
    HUMAN_PROMPT = _constants.HUMAN_PROMPT
    AI_PROMPT = _constants.AI_PROMPT

    def __init__(
        self,
        *,
        api_key: str | None = None,
        auth_token: str | None = None,
        base_url: str | httpx.URL | None = None,
        timeout: Union[float, Timeout, None, NotGiven] = NOT_GIVEN,
        max_retries: int = DEFAULT_MAX_RETRIES,
        default_headers: Mapping[str, str] | None = None,
        default_query: Mapping[str, object] | None = None,
        # Configure a custom httpx client.
        # We provide a `DefaultHttpxClient` class that you can pass to retain the default values we use for `limits`, `timeout` & `follow_redirects`.
        # See the [httpx documentation](https://www.python-httpx.org/api/#client) for more details.
        http_client: httpx.Client | None = None,
        # Enable or disable schema validation for data returned by the API.
        # When enabled an error APIResponseValidationError is raised
        # if the API responds with invalid data for the expected schema.
        #
        # This parameter may be removed or changed in the future.
        # If you rely on this feature, please open a GitHub issue
        # outlining your use-case to help us decide if it should be
        # part of our public interface in the future.
        _strict_response_validation: bool = False,
    ) -> None:
        """Construct a new synchronous anthropic client instance.

        This automatically infers the following arguments from their corresponding environment variables if they are not provided:
        - `api_key` from `ANTHROPIC_API_KEY`
        - `auth_token` from `ANTHROPIC_AUTH_TOKEN`
        """
        if api_key is None:
            api_key = os.environ.get("ANTHROPIC_API_KEY")
        self.api_key = api_key

        if auth_token is None:
            auth_token = os.environ.get("ANTHROPIC_AUTH_TOKEN")
        self.auth_token = auth_token

        if base_url is None:
            base_url = os.environ.get("ANTHROPIC_BASE_URL")
        if base_url is None:
            base_url = f"https://api.anthropic.com"

        super().__init__(
            version=__version__,
            base_url=base_url,
            max_retries=max_retries,
            timeout=timeout,
            http_client=http_client,
            custom_headers=default_headers,
            custom_query=default_query,
            _strict_response_validation=_strict_response_validation,
        )

        self._default_stream_cls = Stream

        self.completions = completions.Completions(self)
        self.messages = messages.Messages(self)
        self.models = models.Models(self)
        self.beta = beta.Beta(self)
        self.with_raw_response = AnthropicWithRawResponse(self)
        self.with_streaming_response = AnthropicWithStreamedResponse(self)

    @property
    @override
    def qs(self) -> Querystring:
        return Querystring(array_format="comma")

    @property
    @override
    def auth_headers(self) -> dict[str, str]:
        if self._api_key_auth:
            return self._api_key_auth
        if self._bearer_auth:
            return self._bearer_auth
        return {}

    @property
    def _api_key_auth(self) -> dict[str, str]:
        api_key = self.api_key
        if api_key is None:
            return {}
        return {"X-Api-Key": api_key}

    @property
    def _bearer_auth(self) -> dict[str, str]:
        auth_token = self.auth_token
        if auth_token is None:
            return {}
        return {"Authorization": f"Bearer {auth_token}"}

    @property
    @override
    def default_headers(self) -> dict[str, str | Omit]:
        return {
            **super().default_headers,
            "X-Stainless-Async": "false",
            "anthropic-version": "2023-06-01",
            **self._custom_headers,
        }

    @override
    def _validate_headers(self, headers: Headers, custom_headers: Headers) -> None:
        if self.api_key and headers.get("X-Api-Key"):
            return
        if isinstance(custom_headers.get("X-Api-Key"), Omit):
            return

        if self.auth_token and headers.get("Authorization"):
            return
        if isinstance(custom_headers.get("Authorization"), Omit):
            return

        raise TypeError(
            '"Could not resolve authentication method. Expected either api_key or auth_token to be set. Or for one of the `X-Api-Key` or `Authorization` headers to be explicitly omitted"'
        )

    def copy(
        self,
        *,
        api_key: str | None = None,
        auth_token: str | None = None,
        base_url: str | httpx.URL | None = None,
        timeout: float | Timeout | None | NotGiven = NOT_GIVEN,
        http_client: httpx.Client | None = None,
        max_retries: int | NotGiven = NOT_GIVEN,
        default_headers: Mapping[str, str] | None = None,
        set_default_headers: Mapping[str, str] | None = None,
        default_query: Mapping[str, object] | None = None,
        set_default_query: Mapping[str, object] | None = None,
        _extra_kwargs: Mapping[str, Any] = {},
    ) -> Self:
        """
        Create a new client instance re-using the same options given to the current client with optional overriding.
        """
        if default_headers is not None and set_default_headers is not None:
            raise ValueError("The `default_headers` and `set_default_headers` arguments are mutually exclusive")

        if default_query is not None and set_default_query is not None:
            raise ValueError("The `default_query` and `set_default_query` arguments are mutually exclusive")

        headers = self._custom_headers
        if default_headers is not None:
            headers = {**headers, **default_headers}
        elif set_default_headers is not None:
            headers = set_default_headers

        params = self._custom_query
        if default_query is not None:
            params = {**params, **default_query}
        elif set_default_query is not None:
            params = set_default_query

        http_client = http_client or self._client
        return self.__class__(
            api_key=api_key or self.api_key,
            auth_token=auth_token or self.auth_token,
            base_url=base_url or self.base_url,
            timeout=self.timeout if isinstance(timeout, NotGiven) else timeout,
            http_client=http_client,
            max_retries=max_retries if is_given(max_retries) else self.max_retries,
            default_headers=headers,
            default_query=params,
            **_extra_kwargs,
        )

    # Alias for `copy` for nicer inline usage, e.g.
    # client.with_options(timeout=10).foo.create(...)
    with_options = copy

    @override
    def _make_status_error(
        self,
        err_msg: str,
        *,
        body: object,
        response: httpx.Response,
    ) -> APIStatusError:
        if response.status_code == 400:
            return _exceptions.BadRequestError(err_msg, response=response, body=body)

        if response.status_code == 401:
            return _exceptions.AuthenticationError(err_msg, response=response, body=body)

        if response.status_code == 403:
            return _exceptions.PermissionDeniedError(err_msg, response=response, body=body)

        if response.status_code == 404:
            return _exceptions.NotFoundError(err_msg, response=response, body=body)

        if response.status_code == 409:
            return _exceptions.ConflictError(err_msg, response=response, body=body)

        if response.status_code == 422:
            return _exceptions.UnprocessableEntityError(err_msg, response=response, body=body)

        if response.status_code == 429:
            return _exceptions.RateLimitError(err_msg, response=response, body=body)

        if response.status_code >= 500:
            return _exceptions.InternalServerError(err_msg, response=response, body=body)
        return APIStatusError(err_msg, response=response, body=body)


class AsyncAnthropic(AsyncAPIClient):
    completions: completions.AsyncCompletions
    messages: messages.AsyncMessages
    models: models.AsyncModels
    beta: beta.AsyncBeta
    with_raw_response: AsyncAnthropicWithRawResponse
    with_streaming_response: AsyncAnthropicWithStreamedResponse

    # client options
    api_key: str | None
    auth_token: str | None

    # constants
    HUMAN_PROMPT = _constants.HUMAN_PROMPT
    AI_PROMPT = _constants.AI_PROMPT

    def __init__(
        self,
        *,
        api_key: str | None = None,
        auth_token: str | None = None,
        base_url: str | httpx.URL | None = None,
        timeout: Union[float, Timeout, None, NotGiven] = NOT_GIVEN,
        max_retries: int = DEFAULT_MAX_RETRIES,
        default_headers: Mapping[str, str] | None = None,
        default_query: Mapping[str, object] | None = None,
        # Configure a custom httpx client.
        # We provide a `DefaultAsyncHttpxClient` class that you can pass to retain the default values we use for `limits`, `timeout` & `follow_redirects`.
        # See the [httpx documentation](https://www.python-httpx.org/api/#asyncclient) for more details.
        http_client: httpx.AsyncClient | None = None,
        # Enable or disable schema validation for data returned by the API.
        # When enabled an error APIResponseValidationError is raised
        # if the API responds with invalid data for the expected schema.
        #
        # This parameter may be removed or changed in the future.
        # If you rely on this feature, please open a GitHub issue
        # outlining your use-case to help us decide if it should be
        # part of our public interface in the future.
        _strict_response_validation: bool = False,
    ) -> None:
        """Construct a new async anthropic client instance.

        This automatically infers the following arguments from their corresponding environment variables if they are not provided:
        - `api_key` from `ANTHROPIC_API_KEY`
        - `auth_token` from `ANTHROPIC_AUTH_TOKEN`
        """
        if api_key is None:
            api_key = os.environ.get("ANTHROPIC_API_KEY")
        self.api_key = api_key

        if auth_token is None:
            auth_token = os.environ.get("ANTHROPIC_AUTH_TOKEN")
        self.auth_token = auth_token

        if base_url is None:
            base_url = os.environ.get("ANTHROPIC_BASE_URL")
        if base_url is None:
            base_url = f"https://api.anthropic.com"

        super().__init__(
            version=__version__,
            base_url=base_url,
            max_retries=max_retries,
            timeout=timeout,
            http_client=http_client,
            custom_headers=default_headers,
            custom_query=default_query,
            _strict_response_validation=_strict_response_validation,
        )

        self._default_stream_cls = AsyncStream

        self.completions = completions.AsyncCompletions(self)
        self.messages = messages.AsyncMessages(self)
        self.models = models.AsyncModels(self)
        self.beta = beta.AsyncBeta(self)
        self.with_raw_response = AsyncAnthropicWithRawResponse(self)
        self.with_streaming_response = AsyncAnthropicWithStreamedResponse(self)

    @property
    @override
    def qs(self) -> Querystring:
        return Querystring(array_format="comma")

    @property
    @override
    def auth_headers(self) -> dict[str, str]:
        if self._api_key_auth:
            return self._api_key_auth
        if self._bearer_auth:
            return self._bearer_auth
        return {}

    @property
    def _api_key_auth(self) -> dict[str, str]:
        api_key = self.api_key
        if api_key is None:
            return {}
        return {"X-Api-Key": api_key}

    @property
    def _bearer_auth(self) -> dict[str, str]:
        auth_token = self.auth_token
        if auth_token is None:
            return {}
        return {"Authorization": f"Bearer {auth_token}"}

    @property
    @override
    def default_headers(self) -> dict[str, str | Omit]:
        return {
            **super().default_headers,
            "X-Stainless-Async": f"async:{get_async_library()}",
            "anthropic-version": "2023-06-01",
            **self._custom_headers,
        }

    @override
    def _validate_headers(self, headers: Headers, custom_headers: Headers) -> None:
        if self.api_key and headers.get("X-Api-Key"):
            return
        if isinstance(custom_headers.get("X-Api-Key"), Omit):
            return

        if self.auth_token and headers.get("Authorization"):
            return
        if isinstance(custom_headers.get("Authorization"), Omit):
            return

        raise TypeError(
            '"Could not resolve authentication method. Expected either api_key or auth_token to be set. Or for one of the `X-Api-Key` or `Authorization` headers to be explicitly omitted"'
        )

    def copy(
        self,
        *,
        api_key: str | None = None,
        auth_token: str | None = None,
        base_url: str | httpx.URL | None = None,
        timeout: float | Timeout | None | NotGiven = NOT_GIVEN,
        http_client: httpx.AsyncClient | None = None,
        max_retries: int | NotGiven = NOT_GIVEN,
        default_headers: Mapping[str, str] | None = None,
        set_default_headers: Mapping[str, str] | None = None,
        default_query: Mapping[str, object] | None = None,
        set_default_query: Mapping[str, object] | None = None,
        _extra_kwargs: Mapping[str, Any] = {},
    ) -> Self:
        """
        Create a new client instance re-using the same options given to the current client with optional overriding.
        """
        if default_headers is not None and set_default_headers is not None:
            raise ValueError("The `default_headers` and `set_default_headers` arguments are mutually exclusive")

        if default_query is not None and set_default_query is not None:
            raise ValueError("The `default_query` and `set_default_query` arguments are mutually exclusive")

        headers = self._custom_headers
        if default_headers is not None:
            headers = {**headers, **default_headers}
        elif set_default_headers is not None:
            headers = set_default_headers

        params = self._custom_query
        if default_query is not None:
            params = {**params, **default_query}
        elif set_default_query is not None:
            params = set_default_query

        http_client = http_client or self._client
        return self.__class__(
            api_key=api_key or self.api_key,
            auth_token=auth_token or self.auth_token,
            base_url=base_url or self.base_url,
            timeout=self.timeout if isinstance(timeout, NotGiven) else timeout,
            http_client=http_client,
            max_retries=max_retries if is_given(max_retries) else self.max_retries,
            default_headers=headers,
            default_query=params,
            **_extra_kwargs,
        )

    # Alias for `copy` for nicer inline usage, e.g.
    # client.with_options(timeout=10).foo.create(...)
    with_options = copy

    @override
    def _make_status_error(
        self,
        err_msg: str,
        *,
        body: object,
        response: httpx.Response,
    ) -> APIStatusError:
        if response.status_code == 400:
            return _exceptions.BadRequestError(err_msg, response=response, body=body)

        if response.status_code == 401:
            return _exceptions.AuthenticationError(err_msg, response=response, body=body)

        if response.status_code == 403:
            return _exceptions.PermissionDeniedError(err_msg, response=response, body=body)

        if response.status_code == 404:
            return _exceptions.NotFoundError(err_msg, response=response, body=body)

        if response.status_code == 409:
            return _exceptions.ConflictError(err_msg, response=response, body=body)

        if response.status_code == 422:
            return _exceptions.UnprocessableEntityError(err_msg, response=response, body=body)

        if response.status_code == 429:
            return _exceptions.RateLimitError(err_msg, response=response, body=body)

        if response.status_code >= 500:
            return _exceptions.InternalServerError(err_msg, response=response, body=body)
        return APIStatusError(err_msg, response=response, body=body)


class AnthropicWithRawResponse:
    def __init__(self, client: Anthropic) -> None:
        self.completions = completions.CompletionsWithRawResponse(client.completions)
        self.messages = messages.MessagesWithRawResponse(client.messages)
        self.models = models.ModelsWithRawResponse(client.models)
        self.beta = beta.BetaWithRawResponse(client.beta)


class AsyncAnthropicWithRawResponse:
    def __init__(self, client: AsyncAnthropic) -> None:
        self.completions = completions.AsyncCompletionsWithRawResponse(client.completions)
        self.messages = messages.AsyncMessagesWithRawResponse(client.messages)
        self.models = models.AsyncModelsWithRawResponse(client.models)
        self.beta = beta.AsyncBetaWithRawResponse(client.beta)


class AnthropicWithStreamedResponse:
    def __init__(self, client: Anthropic) -> None:
        self.completions = completions.CompletionsWithStreamingResponse(client.completions)
        self.messages = messages.MessagesWithStreamingResponse(client.messages)
        self.models = models.ModelsWithStreamingResponse(client.models)
        self.beta = beta.BetaWithStreamingResponse(client.beta)


class AsyncAnthropicWithStreamedResponse:
    def __init__(self, client: AsyncAnthropic) -> None:
        self.completions = completions.AsyncCompletionsWithStreamingResponse(client.completions)
        self.messages = messages.AsyncMessagesWithStreamingResponse(client.messages)
        self.models = models.AsyncModelsWithStreamingResponse(client.models)
        self.beta = beta.AsyncBetaWithStreamingResponse(client.beta)


Client = Anthropic

AsyncClient = AsyncAnthropic
