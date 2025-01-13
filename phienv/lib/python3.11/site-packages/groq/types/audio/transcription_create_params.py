# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import List, Union
from typing_extensions import Literal, Required, TypedDict

from ..._types import FileTypes

__all__ = ["TranscriptionCreateParams"]


class TranscriptionCreateParams(TypedDict, total=False):
    file: Required[FileTypes]
    """
    The audio file object (not file name) to transcribe, in one of these formats:
    flac, mp3, mp4, mpeg, mpga, m4a, ogg, wav, or webm.
    """

    model: Required[Union[str, Literal["whisper-large-v3"]]]
    """ID of the model to use. Only `whisper-large-v3` is currently available."""

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
    """The language of the input audio.

    Supplying the input language in
    [ISO-639-1](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes) format will
    improve accuracy and latency.
    """

    prompt: str
    """An optional text to guide the model's style or continue a previous audio
    segment.

    The [prompt](/docs/speech-text) should match the audio language.
    """

    response_format: Literal["json", "text", "verbose_json"]
    """
    The format of the transcript output, in one of these options: `json`, `text`, or
    `verbose_json`.
    """

    temperature: float
    """The sampling temperature, between 0 and 1.

    Higher values like 0.8 will make the output more random, while lower values like
    0.2 will make it more focused and deterministic. If set to 0, the model will use
    [log probability](https://en.wikipedia.org/wiki/Log_probability) to
    automatically increase the temperature until certain thresholds are hit.
    """

    timestamp_granularities: List[Literal["word", "segment"]]
    """The timestamp granularities to populate for this transcription.

    `response_format` must be set `verbose_json` to use timestamp granularities.
    Either or both of these options are supported: `word`, or `segment`. Note: There
    is no additional latency for segment timestamps, but generating word timestamps
    incurs additional latency.
    """
