from typing import Union
from typing_extensions import Literal

from ...types import (
    Message,
    ContentBlock,
    MessageDeltaEvent as RawMessageDeltaEvent,
    MessageStartEvent as RawMessageStartEvent,
    RawMessageStopEvent,
    ContentBlockDeltaEvent as RawContentBlockDeltaEvent,
    ContentBlockStartEvent as RawContentBlockStartEvent,
    RawContentBlockStopEvent,
)
from ..._models import BaseModel


class TextEvent(BaseModel):
    type: Literal["text"]

    text: str
    """The text delta"""

    snapshot: str
    """The entire accumulated text"""


class InputJsonEvent(BaseModel):
    type: Literal["input_json"]

    partial_json: str
    """A partial JSON string delta

    e.g. `'"San Francisco,'`
    """

    snapshot: object
    """The currently accumulated parsed object.


    e.g. `{'location': 'San Francisco, CA'}`
    """


class MessageStopEvent(RawMessageStopEvent):
    type: Literal["message_stop"]

    message: Message


class ContentBlockStopEvent(RawContentBlockStopEvent):
    type: Literal["content_block_stop"]

    content_block: ContentBlock


MessageStreamEvent = Union[
    TextEvent,
    InputJsonEvent,
    RawMessageStartEvent,
    RawMessageDeltaEvent,
    MessageStopEvent,
    RawContentBlockStartEvent,
    RawContentBlockDeltaEvent,
    ContentBlockStopEvent,
]
