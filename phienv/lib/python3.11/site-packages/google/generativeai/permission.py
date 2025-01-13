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

from typing import Callable

import google.ai.generativelanguage as glm

from google.generativeai.types import permission_types
from google.generativeai.types import retriever_types
from google.generativeai.types import model_types


_RESOURCE_TYPE: dict[str, str] = {
    "corpus": "corpora",
    "corpora": "corpora",
    "tunedmodel": "tunedModels",
    "tunedmodels": "tunedModels",
}


def _to_resource_type(x: str) -> str:
    if isinstance(x, str):
        x = x.lower()
    resource_type = _RESOURCE_TYPE.get(x, None)
    if not resource_type:
        raise ValueError(f"Unsupported resource type. Got: `{x}` instead.")

    return resource_type


def _validate_resource_name(x: str, resource_type: str) -> None:
    if resource_type == "corpora":
        if not retriever_types.valid_name(x):
            raise ValueError(retriever_types.NAME_ERROR_MSG.format(length=len(x), name=x))

    elif resource_type == "tunedModels":
        if not model_types.valid_tuned_model_name(x):
            raise ValueError(model_types.TUNED_MODEL_NAME_ERROR_MSG.format(length=len(x), name=x))

    else:
        raise ValueError(f"Unsupported resource type: {resource_type}")


def _validate_permission_id(x: str) -> None:
    if not permission_types.valid_id(x):
        raise ValueError(permission_types.INVALID_PERMISSION_ID_MSG.format(permission_id=x))


def _get_valid_name_components(name: str) -> str:
    # name is of the format: resource_type/resource_name/permissions/permission_id
    name_path_components = name.split("/")
    if len(name_path_components) != 4:
        raise ValueError(
            f"Invalid name format. Expected format: \
                `resource_type/<resource_name>/permissions/<permission_id>`. Got: `{name}` instead."
        )

    resource_type, resource_name, permission_placeholder, permission_id = name_path_components
    resource_type = _to_resource_type(resource_type)

    permission_id = "/".join([permission_placeholder, permission_id])

    _validate_resource_name(resource_name, resource_type)
    _validate_permission_id(permission_id)

    return "/".join([resource_type, resource_name, permission_id])


def _construct_name(
    name: str | None = None,
    resource_name: str | None = None,
    permission_id: str | int | None = None,
    resource_type: str | None = None,
) -> str:
    # resource_name is the name of the supported resource (corpus or tunedModel as of now) for which the permission is being created.
    if not name:
        # if name is not provided, then try to construct name via provided resource_name and permission_id.
        if not (resource_name and permission_id):
            raise ValueError(
                f"Invalid arguments: Either `name` or both `resource_name` and `permission_id` must be provided. Received name: {name}, resource_name: {resource_name}, permission_id: {permission_id}."
            )
        if resource_type:
            resource_type = _to_resource_type(resource_type)
        else:
            # if resource_type is not provided, then try to infer it from resource_name.
            resource_path_components = resource_name.split("/")
            if len(resource_path_components) != 2:
                raise ValueError(
                    f"Invalid `resource_name` format: Expected format is `resource_type/resource_name` (2 components). Received: `{resource_name}` with {len(resource_path_components)} components."
                )
            resource_type = _to_resource_type(resource_path_components[0])

        if f"{resource_type}/" in resource_name:
            name = f"{resource_name}/"
        else:
            name = f"{resource_type}/{resource_name}/"

        if isinstance(permission_id, int) or "permissions/" not in permission_id:
            name += f"permissions/{permission_id}"
        else:
            name += permission_id

    # if name is provided, override resource_name and permission_id
    name = _get_valid_name_components(name)
    return name


def get_permission(
    name: str | None = None,
    *,
    client: glm.PermissionServiceClient | None = None,
    resource_name: str | None = None,
    permission_id: str | int | None = None,
    resource_type: str | None = None,
) -> permission_types.Permission:
    """Calls the API to retrieve detailed information about a specific permission based on resource type and permission identifiers

    Args:
        name: The name of the permission.
        resource_name: The name of the supported resource for which the permission details are needed.
        permission_id: The name of the permission.
        resource_type: The type of the resource (corpus or tunedModel as of now) for which the permission details are needed.
                        If not provided, it will be inferred from `resource_name`.

    Returns:
        The permission as an instance of `permission_types.Permission`.
    """
    name = _construct_name(
        name=name,
        resource_name=resource_name,
        permission_id=permission_id,
        resource_type=resource_type,
    )
    return permission_types.Permission.get(name=name, client=client)


async def get_permission_async(
    name: str | None = None,
    *,
    client: glm.PermissionServiceAsyncClient | None = None,
    resource_name: str | None = None,
    permission_id: str | int | None = None,
    resource_type: str | None = None,
) -> permission_types.Permission:
    """
    This is the async version of `permission.get_permission`.
    """
    name = _construct_name(
        name=name,
        resource_name=resource_name,
        permission_id=permission_id,
        resource_type=resource_type,
    )
    return await permission_types.Permission.get_async(name=name, client=client)
