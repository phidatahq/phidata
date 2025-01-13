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

from collections.abc import Iterable, Mapping, Sequence
import inspect
import typing
from typing import Any, Callable, Union
from typing_extensions import TypedDict

import pydantic

from google.generativeai import protos

Type = protos.Type

TypeOptions = Union[int, str, Type]

_TYPE_TYPE: dict[TypeOptions, Type] = {
    Type.TYPE_UNSPECIFIED: Type.TYPE_UNSPECIFIED,
    0: Type.TYPE_UNSPECIFIED,
    "type_unspecified": Type.TYPE_UNSPECIFIED,
    "unspecified": Type.TYPE_UNSPECIFIED,
    Type.STRING: Type.STRING,
    1: Type.STRING,
    "type_string": Type.STRING,
    "string": Type.STRING,
    Type.NUMBER: Type.NUMBER,
    2: Type.NUMBER,
    "type_number": Type.NUMBER,
    "number": Type.NUMBER,
    Type.INTEGER: Type.INTEGER,
    3: Type.INTEGER,
    "type_integer": Type.INTEGER,
    "integer": Type.INTEGER,
    Type.BOOLEAN: Type.BOOLEAN,
    4: Type.INTEGER,
    "type_boolean": Type.BOOLEAN,
    "boolean": Type.BOOLEAN,
    Type.ARRAY: Type.ARRAY,
    5: Type.ARRAY,
    "type_array": Type.ARRAY,
    "array": Type.ARRAY,
    Type.OBJECT: Type.OBJECT,
    6: Type.OBJECT,
    "type_object": Type.OBJECT,
    "object": Type.OBJECT,
}


def to_type(x: TypeOptions) -> Type:
    if isinstance(x, str):
        x = x.lower()
    return _TYPE_TYPE[x]


def _generate_schema(
    f: Callable[..., Any],
    *,
    descriptions: Mapping[str, str] | None = None,
    required: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Generates the OpenAPI Schema for a python function.

    Args:
        f: The function to generate an OpenAPI Schema for.
        descriptions: Optional. A `{name: description}` mapping for annotating input
            arguments of the function with user-provided descriptions. It
            defaults to an empty dictionary (i.e. there will not be any
            description for any of the inputs).
        required: Optional. For the user to specify the set of required arguments in
            function calls to `f`. If unspecified, it will be automatically
            inferred from `f`.

    Returns:
        dict[str, Any]: The OpenAPI Schema for the function `f` in JSON format.
    """
    if descriptions is None:
        descriptions = {}
    if required is None:
        required = []
    defaults = dict(inspect.signature(f).parameters)
    fields_dict = {
        name: (
            # 1. We infer the argument type here: use Any rather than None so
            # it will not try to auto-infer the type based on the default value.
            (param.annotation if param.annotation != inspect.Parameter.empty else Any),
            pydantic.Field(
                # 2. We do not support default values for now.
                # default=(
                #     param.default if param.default != inspect.Parameter.empty
                #     else None
                # ),
                # 3. We support user-provided descriptions.
                description=descriptions.get(name, None),
            ),
        )
        for name, param in defaults.items()
        # We do not support *args or **kwargs
        if param.kind
        in (
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.KEYWORD_ONLY,
            inspect.Parameter.POSITIONAL_ONLY,
        )
    }
    parameters = pydantic.create_model(f.__name__, **fields_dict).model_json_schema()
    # Postprocessing
    # 4. Suppress unnecessary title generation:
    #    * https://github.com/pydantic/pydantic/issues/1051
    #    * http://cl/586221780
    parameters.pop("title", None)
    for name, function_arg in parameters.get("properties", {}).items():
        function_arg.pop("title", None)
        annotation = defaults[name].annotation
        # 5. Nullable fields:
        #     * https://github.com/pydantic/pydantic/issues/1270
        #     * https://stackoverflow.com/a/58841311
        #     * https://github.com/pydantic/pydantic/discussions/4872
        if typing.get_origin(annotation) is typing.Union and type(None) in typing.get_args(
            annotation
        ):
            function_arg["nullable"] = True
    # 6. Annotate required fields.
    if required:
        # We use the user-provided "required" fields if specified.
        parameters["required"] = required
    else:
        # Otherwise we infer it from the function signature.
        parameters["required"] = [
            k
            for k in defaults
            if (
                defaults[k].default == inspect.Parameter.empty
                and defaults[k].kind
                in (
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    inspect.Parameter.KEYWORD_ONLY,
                    inspect.Parameter.POSITIONAL_ONLY,
                )
            )
        ]
    schema = dict(name=f.__name__, description=f.__doc__, parameters=parameters)
    return schema


def _rename_schema_fields(schema: dict[str, Any]):
    if schema is None:
        return schema

    schema = schema.copy()

    type_ = schema.pop("type", None)
    if type_ is not None:
        schema["type_"] = type_
    type_ = schema.get("type_", None)
    if type_ is not None:
        schema["type_"] = to_type(type_)

    format_ = schema.pop("format", None)
    if format_ is not None:
        schema["format_"] = format_

    items = schema.pop("items", None)
    if items is not None:
        schema["items"] = _rename_schema_fields(items)

    properties = schema.pop("properties", None)
    if properties is not None:
        schema["properties"] = {k: _rename_schema_fields(v) for k, v in properties.items()}

    return schema


class FunctionDeclaration:
    def __init__(self, *, name: str, description: str, parameters: dict[str, Any] | None = None):
        """A  class wrapping a `protos.FunctionDeclaration`, describes a function for `genai.GenerativeModel`'s `tools`."""
        self._proto = protos.FunctionDeclaration(
            name=name, description=description, parameters=_rename_schema_fields(parameters)
        )

    @property
    def name(self) -> str:
        return self._proto.name

    @property
    def description(self) -> str:
        return self._proto.description

    @property
    def parameters(self) -> protos.Schema:
        return self._proto.parameters

    @classmethod
    def from_proto(cls, proto) -> FunctionDeclaration:
        self = cls(name="", description="", parameters={})
        self._proto = proto
        return self

    def to_proto(self) -> protos.FunctionDeclaration:
        return self._proto

    @staticmethod
    def from_function(function: Callable[..., Any], descriptions: dict[str, str] | None = None):
        """Builds a `CallableFunctionDeclaration` from a python function.

        The function should have type annotations.

        This method is able to generate the schema for arguments annotated with types:

        `AllowedTypes = float | int | str | list[AllowedTypes] | dict`

        This method does not yet build a schema for `TypedDict`, that would allow you to specify the dictionary
        contents. But you can build these manually.
        """

        if descriptions is None:
            descriptions = {}

        schema = _generate_schema(function, descriptions=descriptions)

        return CallableFunctionDeclaration(**schema, function=function)


StructType = dict[str, "ValueType"]
ValueType = Union[float, str, bool, StructType, list["ValueType"], None]


class CallableFunctionDeclaration(FunctionDeclaration):
    """An extension of `FunctionDeclaration` that can be built from a Python function, and is callable.

    Note: The Python function must have type annotations.
    """

    def __init__(
        self,
        *,
        name: str,
        description: str,
        parameters: dict[str, Any] | None = None,
        function: Callable[..., Any],
    ):
        super().__init__(name=name, description=description, parameters=parameters)
        self.function = function

    def __call__(self, fc: protos.FunctionCall) -> protos.FunctionResponse:
        result = self.function(**fc.args)
        if not isinstance(result, dict):
            result = {"result": result}
        return protos.FunctionResponse(name=fc.name, response=result)


FunctionDeclarationType = Union[
    FunctionDeclaration,
    protos.FunctionDeclaration,
    dict[str, Any],
    Callable[..., Any],
]


def _make_function_declaration(
    fun: FunctionDeclarationType,
) -> FunctionDeclaration | protos.FunctionDeclaration:
    if isinstance(fun, (FunctionDeclaration, protos.FunctionDeclaration)):
        return fun
    elif isinstance(fun, dict):
        if "function" in fun:
            return CallableFunctionDeclaration(**fun)
        else:
            return FunctionDeclaration(**fun)
    elif callable(fun):
        return CallableFunctionDeclaration.from_function(fun)
    else:
        raise TypeError(
            f"Invalid argument type: Expected an instance of `genai.FunctionDeclarationType`. Received type: {type(fun).__name__}.",
            fun,
        )


def _encode_fd(fd: FunctionDeclaration | protos.FunctionDeclaration) -> protos.FunctionDeclaration:
    if isinstance(fd, protos.FunctionDeclaration):
        return fd

    return fd.to_proto()


class Tool:
    """A wrapper for `protos.Tool`, Contains a collection of related `FunctionDeclaration` objects."""

    def __init__(self, function_declarations: Iterable[FunctionDeclarationType]):
        # The main path doesn't use this but is seems useful.
        self._function_declarations = [_make_function_declaration(f) for f in function_declarations]
        self._index = {}
        for fd in self._function_declarations:
            name = fd.name
            if name in self._index:
                raise ValueError("")
            self._index[fd.name] = fd

        self._proto = protos.Tool(
            function_declarations=[_encode_fd(fd) for fd in self._function_declarations]
        )

    @property
    def function_declarations(self) -> list[FunctionDeclaration | protos.FunctionDeclaration]:
        return self._function_declarations

    def __getitem__(
        self, name: str | protos.FunctionCall
    ) -> FunctionDeclaration | protos.FunctionDeclaration:
        if not isinstance(name, str):
            name = name.name

        return self._index[name]

    def __call__(self, fc: protos.FunctionCall) -> protos.FunctionResponse | None:
        declaration = self[fc]
        if not callable(declaration):
            return None

        return declaration(fc)

    def to_proto(self):
        return self._proto


class ToolDict(TypedDict):
    function_declarations: list[FunctionDeclarationType]


ToolType = Union[
    Tool, protos.Tool, ToolDict, Iterable[FunctionDeclarationType], FunctionDeclarationType
]


def _make_tool(tool: ToolType) -> Tool:
    if isinstance(tool, Tool):
        return tool
    elif isinstance(tool, protos.Tool):
        return Tool(function_declarations=tool.function_declarations)
    elif isinstance(tool, dict):
        if "function_declarations" in tool:
            return Tool(**tool)
        else:
            fd = tool
            return Tool(function_declarations=[protos.FunctionDeclaration(**fd)])
    elif isinstance(tool, Iterable):
        return Tool(function_declarations=tool)
    else:
        try:
            return Tool(function_declarations=[tool])
        except Exception as e:
            raise TypeError(
                f"Invalid argument type: Expected an instance of `genai.ToolType`. Received type: {type(tool).__name__}.",
                tool,
            ) from e


class FunctionLibrary:
    """A container for a set of `Tool` objects, manages lookup and execution of their functions."""

    def __init__(self, tools: Iterable[ToolType]):
        tools = _make_tools(tools)
        self._tools = list(tools)
        self._index = {}
        for tool in self._tools:
            for declaration in tool.function_declarations:
                name = declaration.name
                if name in self._index:
                    raise ValueError(
                        f"Invalid operation: A `FunctionDeclaration` named '{name}' is already defined. Each `FunctionDeclaration` must have a unique name."
                    )
                self._index[declaration.name] = declaration

    def __getitem__(
        self, name: str | protos.FunctionCall
    ) -> FunctionDeclaration | protos.FunctionDeclaration:
        if not isinstance(name, str):
            name = name.name

        return self._index[name]

    def __call__(self, fc: protos.FunctionCall) -> protos.Part | None:
        declaration = self[fc]
        if not callable(declaration):
            return None

        response = declaration(fc)
        return protos.Part(function_response=response)

    def to_proto(self):
        return [tool.to_proto() for tool in self._tools]


ToolsType = Union[Iterable[ToolType], ToolType]


def _make_tools(tools: ToolsType) -> list[Tool]:
    if isinstance(tools, Iterable) and not isinstance(tools, Mapping):
        tools = [_make_tool(t) for t in tools]
        if len(tools) > 1 and all(len(t.function_declarations) == 1 for t in tools):
            # flatten into a single tool.
            tools = [_make_tool([t.function_declarations[0] for t in tools])]
        return tools
    else:
        tool = tools
        return [_make_tool(tool)]


FunctionLibraryType = Union[FunctionLibrary, ToolsType]


def to_function_library(lib: FunctionLibraryType | None) -> FunctionLibrary | None:
    if lib is None:
        return lib
    elif isinstance(lib, FunctionLibrary):
        return lib
    else:
        return FunctionLibrary(tools=lib)


FunctionCallingMode = protos.FunctionCallingConfig.Mode

# fmt: off
_FUNCTION_CALLING_MODE = {
    1: FunctionCallingMode.AUTO,
    FunctionCallingMode.AUTO: FunctionCallingMode.AUTO,
    "mode_auto": FunctionCallingMode.AUTO,
    "auto": FunctionCallingMode.AUTO,

    2: FunctionCallingMode.ANY,
    FunctionCallingMode.ANY: FunctionCallingMode.ANY,
    "mode_any": FunctionCallingMode.ANY,
    "any": FunctionCallingMode.ANY,

    3: FunctionCallingMode.NONE,
    FunctionCallingMode.NONE: FunctionCallingMode.NONE,
    "mode_none": FunctionCallingMode.NONE,
    "none": FunctionCallingMode.NONE,
}
# fmt: on

FunctionCallingModeType = Union[FunctionCallingMode, str, int]


def to_function_calling_mode(x: FunctionCallingModeType) -> FunctionCallingMode:
    if isinstance(x, str):
        x = x.lower()
    return _FUNCTION_CALLING_MODE[x]


class FunctionCallingConfigDict(TypedDict):
    mode: FunctionCallingModeType
    allowed_function_names: list[str]


FunctionCallingConfigType = Union[
    FunctionCallingModeType, FunctionCallingConfigDict, protos.FunctionCallingConfig
]


def to_function_calling_config(obj: FunctionCallingConfigType) -> protos.FunctionCallingConfig:
    if isinstance(obj, protos.FunctionCallingConfig):
        return obj
    elif isinstance(obj, (FunctionCallingMode, str, int)):
        obj = {"mode": to_function_calling_mode(obj)}
    elif isinstance(obj, dict):
        obj = obj.copy()
        mode = obj.pop("mode")
        obj["mode"] = to_function_calling_mode(mode)
    else:
        raise TypeError(
            "Invalid argument type: Could not convert input to `protos.FunctionCallingConfig`."
            f" Received type: {type(obj).__name__}.",
            obj,
        )

    return protos.FunctionCallingConfig(obj)


class ToolConfigDict:
    function_calling_config: FunctionCallingConfigType


ToolConfigType = Union[ToolConfigDict, protos.ToolConfig]


def to_tool_config(obj: ToolConfigType) -> protos.ToolConfig:
    if isinstance(obj, protos.ToolConfig):
        return obj
    elif isinstance(obj, dict):
        fcc = obj.pop("function_calling_config")
        fcc = to_function_calling_config(fcc)
        obj["function_calling_config"] = fcc
        return protos.ToolConfig(**obj)
    else:
        raise TypeError(
            "Invalid argument type: Could not convert input to `protos.ToolConfig`. "
            f"Received type: {type(obj).__name__}.",
        )
