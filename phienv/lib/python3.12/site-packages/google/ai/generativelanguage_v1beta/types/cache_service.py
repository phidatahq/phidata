# -*- coding: utf-8 -*-
# Copyright 2024 Google LLC
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
#
from __future__ import annotations

from typing import MutableMapping, MutableSequence

from google.protobuf import field_mask_pb2  # type: ignore
import proto  # type: ignore

from google.ai.generativelanguage_v1beta.types import (
    cached_content as gag_cached_content,
)

__protobuf__ = proto.module(
    package="google.ai.generativelanguage.v1beta",
    manifest={
        "ListCachedContentsRequest",
        "ListCachedContentsResponse",
        "CreateCachedContentRequest",
        "GetCachedContentRequest",
        "UpdateCachedContentRequest",
        "DeleteCachedContentRequest",
    },
)


class ListCachedContentsRequest(proto.Message):
    r"""Request to list CachedContents.

    Attributes:
        page_size (int):
            Optional. The maximum number of cached
            contents to return. The service may return fewer
            than this value. If unspecified, some default
            (under maximum) number of items will be
            returned. The maximum value is 1000; values
            above 1000 will be coerced to 1000.
        page_token (str):
            Optional. A page token, received from a previous
            ``ListCachedContents`` call. Provide this to retrieve the
            subsequent page.

            When paginating, all other parameters provided to
            ``ListCachedContents`` must match the call that provided the
            page token.
    """

    page_size: int = proto.Field(
        proto.INT32,
        number=1,
    )
    page_token: str = proto.Field(
        proto.STRING,
        number=2,
    )


class ListCachedContentsResponse(proto.Message):
    r"""Response with CachedContents list.

    Attributes:
        cached_contents (MutableSequence[google.ai.generativelanguage_v1beta.types.CachedContent]):
            List of cached contents.
        next_page_token (str):
            A token, which can be sent as ``page_token`` to retrieve the
            next page. If this field is omitted, there are no subsequent
            pages.
    """

    @property
    def raw_page(self):
        return self

    cached_contents: MutableSequence[
        gag_cached_content.CachedContent
    ] = proto.RepeatedField(
        proto.MESSAGE,
        number=1,
        message=gag_cached_content.CachedContent,
    )
    next_page_token: str = proto.Field(
        proto.STRING,
        number=2,
    )


class CreateCachedContentRequest(proto.Message):
    r"""Request to create CachedContent.

    Attributes:
        cached_content (google.ai.generativelanguage_v1beta.types.CachedContent):
            Required. The cached content to create.
    """

    cached_content: gag_cached_content.CachedContent = proto.Field(
        proto.MESSAGE,
        number=1,
        message=gag_cached_content.CachedContent,
    )


class GetCachedContentRequest(proto.Message):
    r"""Request to read CachedContent.

    Attributes:
        name (str):
            Required. The resource name referring to the content cache
            entry. Format: ``cachedContents/{id}``
    """

    name: str = proto.Field(
        proto.STRING,
        number=1,
    )


class UpdateCachedContentRequest(proto.Message):
    r"""Request to update CachedContent.

    Attributes:
        cached_content (google.ai.generativelanguage_v1beta.types.CachedContent):
            Required. The content cache entry to update
        update_mask (google.protobuf.field_mask_pb2.FieldMask):
            The list of fields to update.
    """

    cached_content: gag_cached_content.CachedContent = proto.Field(
        proto.MESSAGE,
        number=1,
        message=gag_cached_content.CachedContent,
    )
    update_mask: field_mask_pb2.FieldMask = proto.Field(
        proto.MESSAGE,
        number=2,
        message=field_mask_pb2.FieldMask,
    )


class DeleteCachedContentRequest(proto.Message):
    r"""Request to delete CachedContent.

    Attributes:
        name (str):
            Required. The resource name referring to the content cache
            entry Format: ``cachedContents/{id}``
    """

    name: str = proto.Field(
        proto.STRING,
        number=1,
    )


__all__ = tuple(sorted(__protobuf__.manifest))
