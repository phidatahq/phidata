# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing_extensions import Literal, Required, TypedDict

__all__ = ["ChatCompletionAudioParam"]


class ChatCompletionAudioParam(TypedDict, total=False):
    format: Required[Literal["wav", "mp3", "flac", "opus", "pcm16"]]
    """Specifies the output audio format.

    Must be one of `wav`, `mp3`, `flac`, `opus`, or `pcm16`.
    """

    voice: Required[Literal["alloy", "ash", "ballad", "coral", "echo", "sage", "shimmer", "verse"]]
    """The voice the model uses to respond.

    Supported voices are `ash`, `ballad`, `coral`, `sage`, and `verse` (also
    supported but not recommended are `alloy`, `echo`, and `shimmer`; these voices
    are less expressive).
    """
