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

import datetime
from typing import Any, Union
from typing_extensions import TypedDict

from google.rpc.status_pb2 import Status
from google.generativeai.client import get_default_file_client

from google.generativeai import protos

import pprint


class File:
    def __init__(self, proto: protos.File | File | dict):
        if isinstance(proto, File):
            proto = proto.to_proto()
        self._proto = protos.File(proto)

    def to_proto(self) -> protos.File:
        return self._proto

    def to_dict(self) -> dict[str, Any]:
        return type(self._proto).to_dict(self._proto, use_integers_for_enums=False)

    def __str__(self):
        def sort_key(pair):
            name, value = pair
            if name == "name":
                return ""
            elif "time" in name:
                return "zz_" + name
            else:
                return name

        dict_format = dict(sorted(self.to_dict().items(), key=sort_key))
        dict_format = pprint.pformat(dict_format, sort_dicts=False)
        dict_format = "{\n " + dict_format[1:]
        dict_format = "\n   ".join(dict_format.splitlines())
        return dict_format.join(["genai.File(", ")"])

    __repr__ = __str__

    @property
    def name(self) -> str:
        return self._proto.name

    @property
    def display_name(self) -> str:
        return self._proto.display_name

    @property
    def mime_type(self) -> str:
        return self._proto.mime_type

    @property
    def size_bytes(self) -> int:
        return self._proto.size_bytes

    @property
    def create_time(self) -> datetime.datetime:
        return self._proto.create_time

    @property
    def update_time(self) -> datetime.datetime:
        return self._proto.update_time

    @property
    def expiration_time(self) -> datetime.datetime:
        return self._proto.expiration_time

    @property
    def sha256_hash(self) -> bytes:
        return self._proto.sha256_hash

    @property
    def uri(self) -> str:
        return self._proto.uri

    @property
    def state(self) -> protos.File.State:
        return self._proto.state

    @property
    def video_metadata(self) -> protos.VideoMetadata:
        return self._proto.video_metadata

    @property
    def error(self) -> Status:
        return self._proto.error

    def delete(self):
        client = get_default_file_client()
        client.delete_file(name=self.name)


class FileDataDict(TypedDict):
    mime_type: str
    file_uri: str


FileDataType = Union[FileDataDict, protos.FileData, protos.File, File]


def to_file_data(file_data: FileDataType):
    if isinstance(file_data, dict):
        if "file_uri" in file_data:
            file_data = protos.FileData(file_data)
        else:
            file_data = protos.File(file_data)

    if isinstance(file_data, File):
        file_data = file_data.to_proto()

    if isinstance(file_data, protos.File):
        file_data = protos.FileData(
            mime_type=file_data.mime_type,
            file_uri=file_data.uri,
        )

    if isinstance(file_data, protos.FileData):
        return file_data
    else:
        raise TypeError(
            f"Invalid input type. Failed to convert input to `FileData`.\n"
            f"Received an object of type: {type(file_data)}.\n"
            f"Object Value: {file_data}"
        )
