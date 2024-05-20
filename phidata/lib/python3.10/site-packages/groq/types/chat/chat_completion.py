# File generated from our OpenAPI spec by Stainless.

from typing import List, Optional

from ..._models import BaseModel

__all__ = [
    "ChatCompletion",
    "Choice",
    "ChoiceLogprobs",
    "ChoiceLogprobsContent",
    "ChoiceLogprobsContentTopLogprob",
    "ChoiceMessage",
    "ChoiceMessageToolCall",
    "ChoiceMessageToolCallFunction",
    "Usage",
]


class ChoiceLogprobsContentTopLogprob(BaseModel):
    token: Optional[str] = None

    bytes: Optional[List[int]] = None

    logprob: Optional[float] = None


class ChoiceLogprobsContent(BaseModel):
    token: Optional[str] = None

    bytes: Optional[List[int]] = None

    logprob: Optional[float] = None

    top_logprobs: Optional[List[ChoiceLogprobsContentTopLogprob]] = None


class ChoiceLogprobs(BaseModel):
    content: Optional[List[ChoiceLogprobsContent]] = None


class ChoiceMessageToolCallFunction(BaseModel):
    arguments: Optional[str] = None

    name: Optional[str] = None


class ChoiceMessageToolCall(BaseModel):
    id: Optional[str] = None

    function: Optional[ChoiceMessageToolCallFunction] = None

    type: Optional[str] = None


class ChoiceMessage(BaseModel):
    content: str

    role: str

    tool_calls: Optional[List[ChoiceMessageToolCall]] = None


class Choice(BaseModel):
    finish_reason: str

    index: int

    logprobs: ChoiceLogprobs

    message: ChoiceMessage


class Usage(BaseModel):
    completion_time: Optional[float] = None

    completion_tokens: Optional[int] = None

    prompt_time: Optional[float] = None

    prompt_tokens: Optional[int] = None

    queue_time: Optional[float] = None

    total_time: Optional[float] = None

    total_tokens: Optional[int] = None


class ChatCompletion(BaseModel):
    choices: List[Choice]

    id: Optional[str] = None

    created: Optional[int] = None

    model: Optional[str] = None

    object: Optional[str] = None

    system_fingerprint: Optional[str] = None

    usage: Optional[Usage] = None
