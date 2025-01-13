# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import Dict, List, Union, Iterable, Optional
from typing_extensions import Literal, Required, TypeAlias, TypedDict

from .chat_completion_tool_param import ChatCompletionToolParam
from .chat_completion_message_param import ChatCompletionMessageParam
from ..shared_params.function_parameters import FunctionParameters
from .chat_completion_tool_choice_option_param import ChatCompletionToolChoiceOptionParam
from .chat_completion_function_call_option_param import ChatCompletionFunctionCallOptionParam

__all__ = ["CompletionCreateParams", "FunctionCall", "Function", "ResponseFormat"]


class CompletionCreateParams(TypedDict, total=False):
    messages: Required[Iterable[ChatCompletionMessageParam]]
    """A list of messages comprising the conversation so far."""

    model: Required[Union[str, Literal["gemma-7b-it", "llama3-70b-8192", "llama3-8b-8192", "mixtral-8x7b-32768"]]]
    """ID of the model to use.

    For details on which models are compatible with the Chat API, see available
    [models](/docs/models)
    """

    frequency_penalty: Optional[float]
    """Number between -2.0 and 2.0.

    Positive values penalize new tokens based on their existing frequency in the
    text so far, decreasing the model's likelihood to repeat the same line verbatim.
    """

    function_call: Optional[FunctionCall]
    """Deprecated in favor of `tool_choice`.

    Controls which (if any) function is called by the model. `none` means the model
    will not call a function and instead generates a message. `auto` means the model
    can pick between generating a message or calling a function. Specifying a
    particular function via `{"name": "my_function"}` forces the model to call that
    function.

    `none` is the default when no functions are present. `auto` is the default if
    functions are present.
    """

    functions: Optional[Iterable[Function]]
    """Deprecated in favor of `tools`.

    A list of functions the model may generate JSON inputs for.
    """

    logit_bias: Optional[Dict[str, int]]
    """
    This is not yet supported by any of our models. Modify the likelihood of
    specified tokens appearing in the completion.
    """

    logprobs: Optional[bool]
    """
    This is not yet supported by any of our models. Whether to return log
    probabilities of the output tokens or not. If true, returns the log
    probabilities of each output token returned in the `content` of `message`.
    """

    max_tokens: Optional[int]
    """The maximum number of tokens that can be generated in the chat completion.

    The total length of input tokens and generated tokens is limited by the model's
    context length.
    """

    n: Optional[int]
    """How many chat completion choices to generate for each input message.

    Note that the current moment, only n=1 is supported. Other values will result in
    a 400 response.
    """

    parallel_tool_calls: Optional[bool]
    """Whether to enable parallel function calling during tool use."""

    presence_penalty: Optional[float]
    """Number between -2.0 and 2.0.

    Positive values penalize new tokens based on whether they appear in the text so
    far, increasing the model's likelihood to talk about new topics.
    """

    response_format: Optional[ResponseFormat]
    """An object specifying the format that the model must output.

    Setting to `{ "type": "json_object" }` enables JSON mode, which guarantees the
    message the model generates is valid JSON.

    **Important:** when using JSON mode, you **must** also instruct the model to
    produce JSON yourself via a system or user message.
    """

    seed: Optional[int]
    """
    If specified, our system will make a best effort to sample deterministically,
    such that repeated requests with the same `seed` and parameters should return
    the same result. Determinism is not guaranteed, and you should refer to the
    `system_fingerprint` response parameter to monitor changes in the backend.
    """

    service_tier: Optional[Literal["auto", "on_demand", "flex"]]
    """The service tier to use for the request. Defaults to `on_demand`.

    - `auto` will automatically select the highest tier available within the rate
      limits of your organization.
    - `flex` uses the flex tier, which will succeed or fail quickly.
    """

    stop: Union[Optional[str], List[str], None]
    """Up to 4 sequences where the API will stop generating further tokens.

    The returned text will not contain the stop sequence.
    """

    stream: Optional[bool]
    """If set, partial message deltas will be sent.

    Tokens will be sent as data-only
    [server-sent events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events#Event_stream_format)
    as they become available, with the stream terminated by a `data: [DONE]`
    message. [Example code](/docs/text-chat#streaming-a-chat-completion).
    """

    temperature: Optional[float]
    """What sampling temperature to use, between 0 and 2.

    Higher values like 0.8 will make the output more random, while lower values like
    0.2 will make it more focused and deterministic. We generally recommend altering
    this or top_p but not both
    """

    tool_choice: Optional[ChatCompletionToolChoiceOptionParam]
    """
    Controls which (if any) tool is called by the model. `none` means the model will
    not call any tool and instead generates a message. `auto` means the model can
    pick between generating a message or calling one or more tools. `required` means
    the model must call one or more tools. Specifying a particular tool via
    `{"type": "function", "function": {"name": "my_function"}}` forces the model to
    call that tool.

    `none` is the default when no tools are present. `auto` is the default if tools
    are present.
    """

    tools: Optional[Iterable[ChatCompletionToolParam]]
    """A list of tools the model may call.

    Currently, only functions are supported as a tool. Use this to provide a list of
    functions the model may generate JSON inputs for. A max of 128 functions are
    supported.
    """

    top_logprobs: Optional[int]
    """
    This is not yet supported by any of our models. An integer between 0 and 20
    specifying the number of most likely tokens to return at each token position,
    each with an associated log probability. `logprobs` must be set to `true` if
    this parameter is used.
    """

    top_p: Optional[float]
    """
    An alternative to sampling with temperature, called nucleus sampling, where the
    model considers the results of the tokens with top_p probability mass. So 0.1
    means only the tokens comprising the top 10% probability mass are considered. We
    generally recommend altering this or temperature but not both.
    """

    user: Optional[str]
    """
    A unique identifier representing your end-user, which can help us monitor and
    detect abuse.
    """


FunctionCall: TypeAlias = Union[Literal["none", "auto", "required"], ChatCompletionFunctionCallOptionParam]


class Function(TypedDict, total=False):
    name: Required[str]
    """The name of the function to be called.

    Must be a-z, A-Z, 0-9, or contain underscores and dashes, with a maximum length
    of 64.
    """

    description: str
    """
    A description of what the function does, used by the model to choose when and
    how to call the function.
    """

    parameters: FunctionParameters
    """The parameters the functions accepts, described as a JSON Schema object.

    See the docs on [tool use](/docs/tool-use) for examples, and the
    [JSON Schema reference](https://json-schema.org/understanding-json-schema/) for
    documentation about the format.

    Omitting `parameters` defines a function with an empty parameter list.
    """


class ResponseFormat(TypedDict, total=False):
    type: Literal["text", "json_object"]
    """Must be one of `text` or `json_object`."""
