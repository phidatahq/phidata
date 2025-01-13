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

from google.protobuf import duration_pb2  # type: ignore
from google.protobuf import timestamp_pb2  # type: ignore
import proto  # type: ignore

from google.ai.generativelanguage_v1beta.types import content

__protobuf__ = proto.module(
    package="google.ai.generativelanguage.v1beta",
    manifest={
        "CachedContent",
    },
)


class CachedContent(proto.Message):
    r"""Content that has been preprocessed and can be used in
    subsequent request to GenerativeService.

    Cached content can be only used with model it was created for.

    This message has `oneof`_ fields (mutually exclusive fields).
    For each oneof, at most one member field can be set at the same time.
    Setting any member of the oneof automatically clears all other
    members.

    .. _oneof: https://proto-plus-python.readthedocs.io/en/stable/fields.html#oneofs-mutually-exclusive-fields

    Attributes:
        expire_time (google.protobuf.timestamp_pb2.Timestamp):
            Timestamp in UTC of when this resource is considered
            expired. This is *always* provided on output, regardless of
            what was sent on input.

            This field is a member of `oneof`_ ``expiration``.
        ttl (google.protobuf.duration_pb2.Duration):
            Input only. New TTL for this resource, input
            only.

            This field is a member of `oneof`_ ``expiration``.
        name (str):
            Optional. Identifier. The resource name referring to the
            cached content. Format: ``cachedContents/{id}``

            This field is a member of `oneof`_ ``_name``.
        display_name (str):
            Optional. Immutable. The user-generated
            meaningful display name of the cached content.
            Maximum 128 Unicode characters.

            This field is a member of `oneof`_ ``_display_name``.
        model (str):
            Required. Immutable. The name of the ``Model`` to use for
            cached content Format: ``models/{model}``

            This field is a member of `oneof`_ ``_model``.
        system_instruction (google.ai.generativelanguage_v1beta.types.Content):
            Optional. Input only. Immutable. Developer
            set system instruction. Currently text only.

            This field is a member of `oneof`_ ``_system_instruction``.
        contents (MutableSequence[google.ai.generativelanguage_v1beta.types.Content]):
            Optional. Input only. Immutable. The content
            to cache.
        tools (MutableSequence[google.ai.generativelanguage_v1beta.types.Tool]):
            Optional. Input only. Immutable. A list of ``Tools`` the
            model may use to generate the next response
        tool_config (google.ai.generativelanguage_v1beta.types.ToolConfig):
            Optional. Input only. Immutable. Tool config.
            This config is shared for all tools.

            This field is a member of `oneof`_ ``_tool_config``.
        create_time (google.protobuf.timestamp_pb2.Timestamp):
            Output only. Creation time of the cache
            entry.
        update_time (google.protobuf.timestamp_pb2.Timestamp):
            Output only. When the cache entry was last
            updated in UTC time.
        usage_metadata (google.ai.generativelanguage_v1beta.types.CachedContent.UsageMetadata):
            Output only. Metadata on the usage of the
            cached content.
    """

    class UsageMetadata(proto.Message):
        r"""Metadata on the usage of the cached content.

        Attributes:
            total_token_count (int):
                Total number of tokens that the cached
                content consumes.
        """

        total_token_count: int = proto.Field(
            proto.INT32,
            number=1,
        )

    expire_time: timestamp_pb2.Timestamp = proto.Field(
        proto.MESSAGE,
        number=9,
        oneof="expiration",
        message=timestamp_pb2.Timestamp,
    )
    ttl: duration_pb2.Duration = proto.Field(
        proto.MESSAGE,
        number=10,
        oneof="expiration",
        message=duration_pb2.Duration,
    )
    name: str = proto.Field(
        proto.STRING,
        number=1,
        optional=True,
    )
    display_name: str = proto.Field(
        proto.STRING,
        number=11,
        optional=True,
    )
    model: str = proto.Field(
        proto.STRING,
        number=2,
        optional=True,
    )
    system_instruction: content.Content = proto.Field(
        proto.MESSAGE,
        number=3,
        optional=True,
        message=content.Content,
    )
    contents: MutableSequence[content.Content] = proto.RepeatedField(
        proto.MESSAGE,
        number=4,
        message=content.Content,
    )
    tools: MutableSequence[content.Tool] = proto.RepeatedField(
        proto.MESSAGE,
        number=5,
        message=content.Tool,
    )
    tool_config: content.ToolConfig = proto.Field(
        proto.MESSAGE,
        number=6,
        optional=True,
        message=content.ToolConfig,
    )
    create_time: timestamp_pb2.Timestamp = proto.Field(
        proto.MESSAGE,
        number=7,
        message=timestamp_pb2.Timestamp,
    )
    update_time: timestamp_pb2.Timestamp = proto.Field(
        proto.MESSAGE,
        number=8,
        message=timestamp_pb2.Timestamp,
    )
    usage_metadata: UsageMetadata = proto.Field(
        proto.MESSAGE,
        number=12,
        message=UsageMetadata,
    )


__all__ = tuple(sorted(__protobuf__.manifest))
