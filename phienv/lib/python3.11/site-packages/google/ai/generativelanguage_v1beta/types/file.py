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
from google.rpc import status_pb2  # type: ignore
import proto  # type: ignore

__protobuf__ = proto.module(
    package="google.ai.generativelanguage.v1beta",
    manifest={
        "File",
        "VideoMetadata",
    },
)


class File(proto.Message):
    r"""A file uploaded to the API.

    .. _oneof: https://proto-plus-python.readthedocs.io/en/stable/fields.html#oneofs-mutually-exclusive-fields

    Attributes:
        video_metadata (google.ai.generativelanguage_v1beta.types.VideoMetadata):
            Output only. Metadata for a video.

            This field is a member of `oneof`_ ``metadata``.
        name (str):
            Immutable. Identifier. The ``File`` resource name. The ID
            (name excluding the "files/" prefix) can contain up to 40
            characters that are lowercase alphanumeric or dashes (-).
            The ID cannot start or end with a dash. If the name is empty
            on create, a unique name will be generated. Example:
            ``files/123-456``
        display_name (str):
            Optional. The human-readable display name for the ``File``.
            The display name must be no more than 512 characters in
            length, including spaces. Example: "Welcome Image".
        mime_type (str):
            Output only. MIME type of the file.
        size_bytes (int):
            Output only. Size of the file in bytes.
        create_time (google.protobuf.timestamp_pb2.Timestamp):
            Output only. The timestamp of when the ``File`` was created.
        update_time (google.protobuf.timestamp_pb2.Timestamp):
            Output only. The timestamp of when the ``File`` was last
            updated.
        expiration_time (google.protobuf.timestamp_pb2.Timestamp):
            Output only. The timestamp of when the ``File`` will be
            deleted. Only set if the ``File`` is scheduled to expire.
        sha256_hash (bytes):
            Output only. SHA-256 hash of the uploaded
            bytes.
        uri (str):
            Output only. The uri of the ``File``.
        state (google.ai.generativelanguage_v1beta.types.File.State):
            Output only. Processing state of the File.
        error (google.rpc.status_pb2.Status):
            Output only. Error status if File processing
            failed.
    """

    class State(proto.Enum):
        r"""States for the lifecycle of a File.

        Values:
            STATE_UNSPECIFIED (0):
                The default value. This value is used if the
                state is omitted.
            PROCESSING (1):
                File is being processed and cannot be used
                for inference yet.
            ACTIVE (2):
                File is processed and available for
                inference.
            FAILED (10):
                File failed processing.
        """
        STATE_UNSPECIFIED = 0
        PROCESSING = 1
        ACTIVE = 2
        FAILED = 10

    video_metadata: "VideoMetadata" = proto.Field(
        proto.MESSAGE,
        number=12,
        oneof="metadata",
        message="VideoMetadata",
    )
    name: str = proto.Field(
        proto.STRING,
        number=1,
    )
    display_name: str = proto.Field(
        proto.STRING,
        number=2,
    )
    mime_type: str = proto.Field(
        proto.STRING,
        number=3,
    )
    size_bytes: int = proto.Field(
        proto.INT64,
        number=4,
    )
    create_time: timestamp_pb2.Timestamp = proto.Field(
        proto.MESSAGE,
        number=5,
        message=timestamp_pb2.Timestamp,
    )
    update_time: timestamp_pb2.Timestamp = proto.Field(
        proto.MESSAGE,
        number=6,
        message=timestamp_pb2.Timestamp,
    )
    expiration_time: timestamp_pb2.Timestamp = proto.Field(
        proto.MESSAGE,
        number=7,
        message=timestamp_pb2.Timestamp,
    )
    sha256_hash: bytes = proto.Field(
        proto.BYTES,
        number=8,
    )
    uri: str = proto.Field(
        proto.STRING,
        number=9,
    )
    state: State = proto.Field(
        proto.ENUM,
        number=10,
        enum=State,
    )
    error: status_pb2.Status = proto.Field(
        proto.MESSAGE,
        number=11,
        message=status_pb2.Status,
    )


class VideoMetadata(proto.Message):
    r"""Metadata for a video ``File``.

    Attributes:
        video_duration (google.protobuf.duration_pb2.Duration):
            Duration of the video.
    """

    video_duration: duration_pb2.Duration = proto.Field(
        proto.MESSAGE,
        number=1,
        message=duration_pb2.Duration,
    )


__all__ = tuple(sorted(__protobuf__.manifest))
