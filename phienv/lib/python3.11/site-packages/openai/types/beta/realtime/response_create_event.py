# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from typing import List, Union, Optional
from typing_extensions import Literal

from ...._models import BaseModel
from .conversation_item import ConversationItem

__all__ = ["ResponseCreateEvent", "Response", "ResponseTool"]


class ResponseTool(BaseModel):
    description: Optional[str] = None
    """
    The description of the function, including guidance on when and how to call it,
    and guidance about what to tell the user when calling (if anything).
    """

    name: Optional[str] = None
    """The name of the function."""

    parameters: Optional[object] = None
    """Parameters of the function in JSON Schema."""

    type: Optional[Literal["function"]] = None
    """The type of the tool, i.e. `function`."""


class Response(BaseModel):
    conversation: Union[str, Literal["auto", "none"], None] = None
    """Controls which conversation the response is added to.

    Currently supports `auto` and `none`, with `auto` as the default value. The
    `auto` value means that the contents of the response will be added to the
    default conversation. Set this to `none` to create an out-of-band response which
    will not add items to default conversation.
    """

    input: Optional[List[ConversationItem]] = None
    """Input items to include in the prompt for the model.

    Creates a new context for this response, without including the default
    conversation. Can include references to items from the default conversation.
    """

    instructions: Optional[str] = None
    """The default system instructions (i.e.

    system message) prepended to model calls. This field allows the client to guide
    the model on desired responses. The model can be instructed on response content
    and format, (e.g. "be extremely succinct", "act friendly", "here are examples of
    good responses") and on audio behavior (e.g. "talk quickly", "inject emotion
    into your voice", "laugh frequently"). The instructions are not guaranteed to be
    followed by the model, but they provide guidance to the model on the desired
    behavior.

    Note that the server sets default instructions which will be used if this field
    is not set and are visible in the `session.created` event at the start of the
    session.
    """

    max_response_output_tokens: Union[int, Literal["inf"], None] = None
    """
    Maximum number of output tokens for a single assistant response, inclusive of
    tool calls. Provide an integer between 1 and 4096 to limit output tokens, or
    `inf` for the maximum available tokens for a given model. Defaults to `inf`.
    """

    metadata: Optional[object] = None
    """Set of 16 key-value pairs that can be attached to an object.

    This can be useful for storing additional information about the object in a
    structured format. Keys can be a maximum of 64 characters long and values can be
    a maximum of 512 characters long.
    """

    modalities: Optional[List[Literal["text", "audio"]]] = None
    """The set of modalities the model can respond with.

    To disable audio, set this to ["text"].
    """

    output_audio_format: Optional[Literal["pcm16", "g711_ulaw", "g711_alaw"]] = None
    """The format of output audio. Options are `pcm16`, `g711_ulaw`, or `g711_alaw`."""

    temperature: Optional[float] = None
    """Sampling temperature for the model, limited to [0.6, 1.2]. Defaults to 0.8."""

    tool_choice: Optional[str] = None
    """How the model chooses tools.

    Options are `auto`, `none`, `required`, or specify a function, like
    `{"type": "function", "function": {"name": "my_function"}}`.
    """

    tools: Optional[List[ResponseTool]] = None
    """Tools (functions) available to the model."""

    voice: Optional[Literal["alloy", "ash", "ballad", "coral", "echo", "sage", "shimmer", "verse"]] = None
    """The voice the model uses to respond.

    Voice cannot be changed during the session once the model has responded with
    audio at least once. Current voice options are `alloy`, `ash`, `ballad`,
    `coral`, `echo` `sage`, `shimmer` and `verse`.
    """


class ResponseCreateEvent(BaseModel):
    type: Literal["response.create"]
    """The event type, must be `response.create`."""

    event_id: Optional[str] = None
    """Optional client-generated ID used to identify this event."""

    response: Optional[Response] = None
    """Create a new Realtime response with these parameters"""
