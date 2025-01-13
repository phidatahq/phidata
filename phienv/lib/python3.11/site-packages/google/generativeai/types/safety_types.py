# -*- coding: utf-8 -*-
# Copyright 2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from __future__ import annotations

from collections.abc import Mapping

import enum
import typing
from typing import Dict, Iterable, List, Union

from typing_extensions import TypedDict


from google.generativeai import protos
from google.generativeai import string_utils


__all__ = [
    "HarmCategory",
    "HarmProbability",
    "HarmBlockThreshold",
    "BlockedReason",
    "ContentFilterDict",
    "SafetyRatingDict",
    "SafetySettingDict",
    "SafetyFeedbackDict",
]

# These are basic python enums, it's okay to expose them
HarmProbability = protos.SafetyRating.HarmProbability
HarmBlockThreshold = protos.SafetySetting.HarmBlockThreshold
BlockedReason = protos.ContentFilter.BlockedReason

import proto


class HarmCategory(proto.Enum):
    """
    Harm Categories supported by the gemini-family model
    """

    HARM_CATEGORY_UNSPECIFIED = protos.HarmCategory.HARM_CATEGORY_UNSPECIFIED.value
    HARM_CATEGORY_HARASSMENT = protos.HarmCategory.HARM_CATEGORY_HARASSMENT.value
    HARM_CATEGORY_HATE_SPEECH = protos.HarmCategory.HARM_CATEGORY_HATE_SPEECH.value
    HARM_CATEGORY_SEXUALLY_EXPLICIT = protos.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT.value
    HARM_CATEGORY_DANGEROUS_CONTENT = protos.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT.value


HarmCategoryOptions = Union[str, int, HarmCategory]

# fmt: off
_HARM_CATEGORIES: Dict[HarmCategoryOptions, protos.HarmCategory] = {
    protos.HarmCategory.HARM_CATEGORY_UNSPECIFIED: protos.HarmCategory.HARM_CATEGORY_UNSPECIFIED,
    HarmCategory.HARM_CATEGORY_UNSPECIFIED: protos.HarmCategory.HARM_CATEGORY_UNSPECIFIED,
    0: protos.HarmCategory.HARM_CATEGORY_UNSPECIFIED,
    "harm_category_unspecified": protos.HarmCategory.HARM_CATEGORY_UNSPECIFIED,
    "unspecified": protos.HarmCategory.HARM_CATEGORY_UNSPECIFIED,
    
    7: protos.HarmCategory.HARM_CATEGORY_HARASSMENT,
    protos.HarmCategory.HARM_CATEGORY_HARASSMENT: protos.HarmCategory.HARM_CATEGORY_HARASSMENT,
    HarmCategory.HARM_CATEGORY_HARASSMENT: protos.HarmCategory.HARM_CATEGORY_HARASSMENT,
    "harm_category_harassment": protos.HarmCategory.HARM_CATEGORY_HARASSMENT,
    "harassment": protos.HarmCategory.HARM_CATEGORY_HARASSMENT,

    8: protos.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
    protos.HarmCategory.HARM_CATEGORY_HATE_SPEECH: protos.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: protos.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
    'harm_category_hate_speech': protos.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
    'hate_speech': protos.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
    'hate': protos.HarmCategory.HARM_CATEGORY_HATE_SPEECH,

    9: protos.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
    protos.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: protos.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: protos.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
    "harm_category_sexually_explicit": protos.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
    "harm_category_sexual": protos.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
    "sexually_explicit": protos.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
    "sexual": protos.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
    "sex": protos.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,

    10: protos.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
    protos.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: protos.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: protos.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
    "harm_category_dangerous_content": protos.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
    "harm_category_dangerous": protos.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
    "dangerous": protos.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
    "danger": protos.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
}
# fmt: on


def to_harm_category(x: HarmCategoryOptions) -> protos.HarmCategory:
    if isinstance(x, str):
        x = x.lower()
    return _HARM_CATEGORIES[x]


HarmBlockThresholdOptions = Union[str, int, HarmBlockThreshold]

# fmt: off
_BLOCK_THRESHOLDS: Dict[HarmBlockThresholdOptions, HarmBlockThreshold] = {
    HarmBlockThreshold.HARM_BLOCK_THRESHOLD_UNSPECIFIED: HarmBlockThreshold.HARM_BLOCK_THRESHOLD_UNSPECIFIED,
    0: HarmBlockThreshold.HARM_BLOCK_THRESHOLD_UNSPECIFIED,
    "harm_block_threshold_unspecified": HarmBlockThreshold.HARM_BLOCK_THRESHOLD_UNSPECIFIED,
    "block_threshold_unspecified": HarmBlockThreshold.HARM_BLOCK_THRESHOLD_UNSPECIFIED,
    "unspecified": HarmBlockThreshold.HARM_BLOCK_THRESHOLD_UNSPECIFIED,

    HarmBlockThreshold.BLOCK_LOW_AND_ABOVE: HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
    1: HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
    "block_low_and_above": HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
    "low": HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,

    HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    2: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    "block_medium_and_above": HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    "medium": HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    "med": HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,

    HarmBlockThreshold.BLOCK_ONLY_HIGH: HarmBlockThreshold.BLOCK_ONLY_HIGH,
    3: HarmBlockThreshold.BLOCK_ONLY_HIGH,
    "block_only_high": HarmBlockThreshold.BLOCK_ONLY_HIGH,
    "high": HarmBlockThreshold.BLOCK_ONLY_HIGH,

    HarmBlockThreshold.BLOCK_NONE: HarmBlockThreshold.BLOCK_NONE,
    4: HarmBlockThreshold.BLOCK_NONE,
    "block_none": HarmBlockThreshold.BLOCK_NONE,
}
# fmt: on


def to_block_threshold(x: HarmBlockThresholdOptions) -> HarmBlockThreshold:
    if isinstance(x, str):
        x = x.lower()
    return _BLOCK_THRESHOLDS[x]


class ContentFilterDict(TypedDict):
    reason: BlockedReason
    message: str

    __doc__ = string_utils.strip_oneof(protos.ContentFilter.__doc__)


def convert_filters_to_enums(
    filters: Iterable[dict],
) -> List[ContentFilterDict]:
    result = []
    for f in filters:
        f = f.copy()
        f["reason"] = BlockedReason(f["reason"])
        f = typing.cast(ContentFilterDict, f)
        result.append(f)
    return result


class SafetyRatingDict(TypedDict):
    category: protos.HarmCategory
    probability: HarmProbability

    __doc__ = string_utils.strip_oneof(protos.SafetyRating.__doc__)


def convert_rating_to_enum(rating: dict) -> SafetyRatingDict:
    return {
        "category": protos.HarmCategory(rating["category"]),
        "probability": HarmProbability(rating["probability"]),
    }


def convert_ratings_to_enum(ratings: Iterable[dict]) -> List[SafetyRatingDict]:
    result = []
    for r in ratings:
        result.append(convert_rating_to_enum(r))
    return result


class SafetySettingDict(TypedDict):
    category: protos.HarmCategory
    threshold: HarmBlockThreshold

    __doc__ = string_utils.strip_oneof(protos.SafetySetting.__doc__)


class LooseSafetySettingDict(TypedDict):
    category: HarmCategoryOptions
    threshold: HarmBlockThresholdOptions


EasySafetySetting = Mapping[HarmCategoryOptions, HarmBlockThresholdOptions]
EasySafetySettingDict = dict[HarmCategoryOptions, HarmBlockThresholdOptions]

SafetySettingOptions = Union[
    HarmBlockThresholdOptions, EasySafetySetting, Iterable[LooseSafetySettingDict], None
]


def _expand_block_threshold(block_threshold: HarmBlockThresholdOptions):
    block_threshold = to_block_threshold(block_threshold)
    hc = set(_HARM_CATEGORIES.values())
    hc.remove(protos.HarmCategory.HARM_CATEGORY_UNSPECIFIED)
    return {category: block_threshold for category in hc}


def to_easy_safety_dict(settings: SafetySettingOptions) -> EasySafetySettingDict:
    if settings is None:
        return {}

    if isinstance(settings, (int, str, HarmBlockThreshold)):
        settings = _expand_block_threshold(settings)

    if isinstance(settings, Mapping):
        return {to_harm_category(key): to_block_threshold(value) for key, value in settings.items()}

    else:  # Iterable
        result = {}
        for setting in settings:
            if isinstance(setting, protos.SafetySetting):
                result[to_harm_category(setting.category)] = to_block_threshold(setting.threshold)
            elif isinstance(setting, dict):
                result[to_harm_category(setting["category"])] = to_block_threshold(
                    setting["threshold"]
                )
            else:
                raise ValueError(
                    f"Could not understand safety setting:\n  {type(setting)=}\n  {setting=}"
                )
        return result


def normalize_safety_settings(
    settings: SafetySettingOptions,
) -> list[SafetySettingDict] | None:
    if settings is None:
        return None

    if isinstance(settings, (int, str, HarmBlockThreshold)):
        settings = _expand_block_threshold(settings)

    if isinstance(settings, Mapping):
        return [
            {
                "category": to_harm_category(key),
                "threshold": to_block_threshold(value),
            }
            for key, value in settings.items()
        ]
    else:
        return [
            {
                "category": to_harm_category(d["category"]),
                "threshold": to_block_threshold(d["threshold"]),
            }
            for d in settings
        ]


def convert_setting_to_enum(setting: dict) -> SafetySettingDict:
    return {
        "category": protos.HarmCategory(setting["category"]),
        "threshold": HarmBlockThreshold(setting["threshold"]),
    }


class SafetyFeedbackDict(TypedDict):
    rating: SafetyRatingDict
    setting: SafetySettingDict

    __doc__ = string_utils.strip_oneof(protos.SafetyFeedback.__doc__)


def convert_safety_feedback_to_enums(
    safety_feedback: Iterable[dict],
) -> List[SafetyFeedbackDict]:
    result = []
    for sf in safety_feedback:
        result.append(
            {
                "rating": convert_rating_to_enum(sf["rating"]),
                "setting": convert_setting_to_enum(sf["setting"]),
            }
        )
    return result


def convert_candidate_enums(candidates):
    result = []
    for candidate in candidates:
        candidate = candidate.copy()
        candidate["safety_ratings"] = convert_ratings_to_enum(candidate["safety_ratings"])
        result.append(candidate)
    return result
