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

import os
import pathlib
import mimetypes
from typing import Iterable
import logging
from google.generativeai import protos
from itertools import islice
from io import IOBase

from google.generativeai.types import file_types

from google.generativeai.client import get_default_file_client

__all__ = ["upload_file", "get_file", "list_files", "delete_file"]

mimetypes.add_type("image/webp", ".webp")


def upload_file(
    path: str | pathlib.Path | os.PathLike | IOBase,
    *,
    mime_type: str | None = None,
    name: str | None = None,
    display_name: str | None = None,
    resumable: bool = True,
) -> file_types.File:
    """Calls the API to upload a file using a supported file service.

    Args:
        path: The path to the file or a file-like object (e.g., BytesIO) to be uploaded.
        mime_type: The MIME type of the file. If not provided, it will be
            inferred from the file extension.
        name: The name of the file in the destination (e.g., 'files/sample-image').
            If not provided, a system generated ID will be created.
        display_name: Optional display name of the file.
        resumable: Whether to use the resumable upload protocol. By default, this is enabled.
            See details at
            https://googleapis.github.io/google-api-python-client/docs/epy/googleapiclient.http.MediaFileUpload-class.html#resumable

    Returns:
        file_types.File: The response of the uploaded file.
    """
    client = get_default_file_client()

    if isinstance(path, IOBase):
        if mime_type is None:
            raise ValueError(
                "Unknown mime type: When passing a file like object to `path` (instead of a\n"
                "    path-like object) you must set the `mime_type` argument"
            )
    else:
        path = pathlib.Path(os.fspath(path))

        if display_name is None:
            display_name = path.name

        if mime_type is None:
            mime_type, _ = mimetypes.guess_type(path)

        if mime_type is None:
            raise ValueError(
                "Unknown mime type: Could not determine the mimetype for your file\n"
                "    please set the `mime_type` argument"
            )

    if name is not None and "/" not in name:
        name = f"files/{name}"

    response = client.create_file(
        path=path, mime_type=mime_type, name=name, display_name=display_name, resumable=resumable
    )
    return file_types.File(response)


def list_files(page_size=100) -> Iterable[file_types.File]:
    """Calls the API to list files using a supported file service."""
    client = get_default_file_client()

    response = client.list_files(protos.ListFilesRequest(page_size=page_size))
    for proto in response:
        yield file_types.File(proto)


def get_file(name: str) -> file_types.File:
    """Calls the API to retrieve a specified file using a supported file service."""
    if "/" not in name:
        name = f"files/{name}"
    client = get_default_file_client()
    return file_types.File(client.get_file(name=name))


def delete_file(name: str | file_types.File | protos.File):
    """Calls the API to permanently delete a specified file using a supported file service."""
    if isinstance(name, (file_types.File, protos.File)):
        name = name.name
    elif "/" not in name:
        name = f"files/{name}"
    request = protos.DeleteFileRequest(name=name)
    client = get_default_file_client()
    client.delete_file(request=request)
