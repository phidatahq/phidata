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

import google.api_core.timeout
import google.api_core.retry

import collections
import dataclasses

from typing import Union
from typing_extensions import TypedDict

__all__ = ["RequestOptions", "RequestOptionsType"]


class RequestOptionsDict(TypedDict, total=False):
    retry: google.api_core.retry.Retry
    timeout: Union[int, float, google.api_core.timeout.TimeToDeadlineTimeout]


@dataclasses.dataclass(init=False)
class RequestOptions(collections.abc.Mapping):
    """Request options

    >>> import google.generativeai as genai
    >>> from google.generativeai.types import RequestOptions
    >>> from google.api_core import retry
    >>>
    >>> model = genai.GenerativeModel()
    >>> response = model.generate_content('Hello',
    ...     request_options=RequestOptions(
    ...         retry=retry.Retry(initial=10, multiplier=2, maximum=60, timeout=300)))
    >>> response = model.generate_content('Hello',
    ...     request_options=RequestOptions(timeout=600)))

    Args:
        retry: Refer to [retry docs](https://googleapis.dev/python/google-api-core/latest/retry.html) for details.
        timeout: In seconds (or provide a [TimeToDeadlineTimeout](https://googleapis.dev/python/google-api-core/latest/timeout.html) object).
    """

    retry: google.api_core.retry.Retry | None
    timeout: int | float | google.api_core.timeout.TimeToDeadlineTimeout | None

    def __init__(
        self,
        *,
        retry: google.api_core.retry.Retry | None = None,
        timeout: int | float | google.api_core.timeout.TimeToDeadlineTimeout | None = None,
    ):
        self.retry = retry
        self.timeout = timeout

    # Inherit from Mapping for **unpacking
    def __getitem__(self, item):
        if item == "retry":
            return self.retry
        elif item == "timeout":
            return self.timeout
        else:
            raise KeyError(
                f"Invalid key: 'RequestOptions' does not contain a key named '{item}'. "
                "Please use a valid key."
            )

    def __iter__(self):
        yield "retry"
        yield "timeout"

    def __len__(self):
        return 2


RequestOptionsType = Union[RequestOptions, RequestOptionsDict]
