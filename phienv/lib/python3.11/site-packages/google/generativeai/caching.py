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
from __future__ import annotations

import datetime
import textwrap
from typing import Iterable, Optional

from google.generativeai import protos
from google.generativeai.types import caching_types
from google.generativeai.types import content_types
from google.generativeai.client import get_default_cache_client

from google.protobuf import field_mask_pb2

_USER_ROLE = "user"
_MODEL_ROLE = "model"


class CachedContent:
    """Cached content resource."""

    def __init__(self, name):
        """Fetches a `CachedContent` resource.

        Identical to `CachedContent.get`.

        Args:
            name: The resource name referring to the cached content.
        """
        client = get_default_cache_client()

        if "cachedContents/" not in name:
            name = "cachedContents/" + name

        request = protos.GetCachedContentRequest(name=name)
        response = client.get_cached_content(request)
        self._proto = response

    @property
    def name(self) -> str:
        return self._proto.name

    @property
    def model(self) -> str:
        return self._proto.model

    @property
    def display_name(self) -> str:
        return self._proto.display_name

    @property
    def usage_metadata(self) -> protos.CachedContent.UsageMetadata:
        return self._proto.usage_metadata

    @property
    def create_time(self) -> datetime.datetime:
        return self._proto.create_time

    @property
    def update_time(self) -> datetime.datetime:
        return self._proto.update_time

    @property
    def expire_time(self) -> datetime.datetime:
        return self._proto.expire_time

    def __str__(self):
        return textwrap.dedent(
            f"""\
            CachedContent(
                name='{self.name}',
                model='{self.model}',
                display_name='{self.display_name}',
                usage_metadata={'{'}
                    'total_token_count': {self.usage_metadata.total_token_count},
                {'}'},
                create_time={self.create_time},
                update_time={self.update_time},
                expire_time={self.expire_time}
            )"""
        )

    __repr__ = __str__

    @classmethod
    def _from_obj(cls, obj: CachedContent | protos.CachedContent | dict) -> CachedContent:
        """Creates an instance of CachedContent form an object, without calling `get`."""
        self = cls.__new__(cls)
        self._proto = protos.CachedContent()
        self._update(obj)
        return self

    def _update(self, updates):
        """Updates this instance inplace, does not call the API's `update` method"""
        if isinstance(updates, CachedContent):
            updates = updates._proto

        if not isinstance(updates, dict):
            updates = type(updates).to_dict(updates, including_default_value_fields=False)

        for key, value in updates.items():
            setattr(self._proto, key, value)

    @staticmethod
    def _prepare_create_request(
        model: str,
        *,
        display_name: str | None = None,
        system_instruction: Optional[content_types.ContentType] = None,
        contents: Optional[content_types.ContentsType] = None,
        tools: Optional[content_types.FunctionLibraryType] = None,
        tool_config: Optional[content_types.ToolConfigType] = None,
        ttl: Optional[caching_types.TTLTypes] = None,
        expire_time: Optional[caching_types.ExpireTimeTypes] = None,
    ) -> protos.CreateCachedContentRequest:
        """Prepares a CreateCachedContentRequest."""
        if ttl and expire_time:
            raise ValueError(
                "Exclusive arguments: Please provide either `ttl` or `expire_time`, not both."
            )

        if "/" not in model:
            model = "models/" + model

        if display_name and len(display_name) > 128:
            raise ValueError("`display_name` must be no more than 128 unicode characters.")

        if system_instruction:
            system_instruction = content_types.to_content(system_instruction)

        tools_lib = content_types.to_function_library(tools)
        if tools_lib:
            tools_lib = tools_lib.to_proto()

        if tool_config:
            tool_config = content_types.to_tool_config(tool_config)

        if contents:
            contents = content_types.to_contents(contents)
            if not contents[-1].role:
                contents[-1].role = _USER_ROLE

        ttl = caching_types.to_optional_ttl(ttl)
        expire_time = caching_types.to_optional_expire_time(expire_time)

        cached_content = protos.CachedContent(
            model=model,
            display_name=display_name,
            system_instruction=system_instruction,
            contents=contents,
            tools=tools_lib,
            tool_config=tool_config,
            ttl=ttl,
            expire_time=expire_time,
        )

        return protos.CreateCachedContentRequest(cached_content=cached_content)

    @classmethod
    def create(
        cls,
        model: str,
        *,
        display_name: str | None = None,
        system_instruction: Optional[content_types.ContentType] = None,
        contents: Optional[content_types.ContentsType] = None,
        tools: Optional[content_types.FunctionLibraryType] = None,
        tool_config: Optional[content_types.ToolConfigType] = None,
        ttl: Optional[caching_types.TTLTypes] = None,
        expire_time: Optional[caching_types.ExpireTimeTypes] = None,
    ) -> CachedContent:
        """Creates `CachedContent` resource.

        Args:
            model: The name of the `model` to use for cached content creation.
                   Any `CachedContent` resource can be only used with the
                   `model` it was created for.
            display_name: The user-generated meaningful display name
                          of the cached content. `display_name` must be no
                          more than 128 unicode characters.
            system_instruction: Developer set system instruction.
            contents: Contents to cache.
            tools: A list of `Tools` the model may use to generate response.
            tool_config: Config to apply to all tools.
            ttl: TTL for cached resource (in seconds). Defaults to 1 hour.
                 `ttl` and `expire_time` are exclusive arguments.
            expire_time: Expiration time for cached resource.
                         `ttl` and `expire_time` are exclusive arguments.

        Returns:
            `CachedContent` resource with specified name.
        """
        client = get_default_cache_client()

        request = cls._prepare_create_request(
            model=model,
            display_name=display_name,
            system_instruction=system_instruction,
            contents=contents,
            tools=tools,
            tool_config=tool_config,
            ttl=ttl,
            expire_time=expire_time,
        )

        response = client.create_cached_content(request)
        result = CachedContent._from_obj(response)
        return result

    @classmethod
    def get(cls, name: str) -> CachedContent:
        """Fetches required `CachedContent` resource.

        Args:
            name: The resource name referring to the cached content.

        Returns:
            `CachedContent` resource with specified `name`.
        """
        client = get_default_cache_client()

        if "cachedContents/" not in name:
            name = "cachedContents/" + name

        request = protos.GetCachedContentRequest(name=name)
        response = client.get_cached_content(request)
        result = CachedContent._from_obj(response)
        return result

    @classmethod
    def list(cls, page_size: Optional[int] = 1) -> Iterable[CachedContent]:
        """Lists `CachedContent` objects associated with the project.

        Args:
            page_size: The maximum number of permissions to return (per page).
            The service may return fewer `CachedContent` objects.

        Returns:
            A paginated list of `CachedContent` objects.
        """
        client = get_default_cache_client()

        request = protos.ListCachedContentsRequest(page_size=page_size)
        for cached_content in client.list_cached_contents(request):
            cached_content = CachedContent._from_obj(cached_content)
            yield cached_content

    def delete(self) -> None:
        """Deletes `CachedContent` resource."""
        client = get_default_cache_client()

        request = protos.DeleteCachedContentRequest(name=self.name)
        client.delete_cached_content(request)
        return

    def update(
        self,
        *,
        ttl: Optional[caching_types.TTLTypes] = None,
        expire_time: Optional[caching_types.ExpireTimeTypes] = None,
    ) -> None:
        """Updates requested `CachedContent` resource.

        Args:
            ttl: TTL for cached resource (in seconds). Defaults to 1 hour.
                 `ttl` and `expire_time` are exclusive arguments.
            expire_time: Expiration time for cached resource.
                         `ttl` and `expire_time` are exclusive arguments.
        """
        client = get_default_cache_client()

        if ttl and expire_time:
            raise ValueError(
                "Exclusive arguments: Please provide either `ttl` or `expire_time`, not both."
            )

        ttl = caching_types.to_optional_ttl(ttl)
        expire_time = caching_types.to_optional_expire_time(expire_time)

        updates = protos.CachedContent(
            name=self.name,
            ttl=ttl,
            expire_time=expire_time,
        )

        field_mask = field_mask_pb2.FieldMask()

        if ttl:
            field_mask.paths.append("ttl")
        elif expire_time:
            field_mask.paths.append("expire_time")
        else:
            raise ValueError(
                f"Bad update name: Only `ttl`  or `expire_time` can be updated for `CachedContent`."
            )

        request = protos.UpdateCachedContentRequest(cached_content=updates, update_mask=field_mask)
        updated_cc = client.update_cached_content(request)
        self._update(updated_cc)

        return
