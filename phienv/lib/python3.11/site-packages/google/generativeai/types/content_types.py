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

from collections.abc import Iterable, Mapping, Sequence
import io
import inspect
import mimetypes
import pathlib
import typing
from typing import Any, Callable, Union
from typing_extensions import TypedDict

import pydantic

from google.generativeai.types import file_types
from google.generativeai import protos

if typing.TYPE_CHECKING:
    import PIL.Image
    import PIL.ImageFile
    import IPython.display

    IMAGE_TYPES = (PIL.Image.Image, IPython.display.Image)
else:
    IMAGE_TYPES = ()
    try:
        import PIL.Image
        import PIL.ImageFile

        IMAGE_TYPES = IMAGE_TYPES + (PIL.Image.Image,)
    except ImportError:
        PIL = None

    try:
        import IPython.display

        IMAGE_TYPES = IMAGE_TYPES + (IPython.display.Image,)
    except ImportError:
        IPython = None


__all__ = [
    "BlobDict",
    "BlobType",
    "PartDict",
    "PartType",
    "ContentDict",
    "ContentType",
    "StrictContentType",
    "ContentsType",
    "FunctionDeclaration",
    "CallableFunctionDeclaration",
    "FunctionDeclarationType",
    "Tool",
    "ToolDict",
    "ToolsType",
    "FunctionLibrary",
    "FunctionLibraryType",
]

Mode = protos.DynamicRetrievalConfig.Mode

ModeOptions = Union[int, str, Mode]

_MODE: dict[ModeOptions, Mode] = {
    Mode.MODE_UNSPECIFIED: Mode.MODE_UNSPECIFIED,
    0: Mode.MODE_UNSPECIFIED,
    "mode_unspecified": Mode.MODE_UNSPECIFIED,
    "unspecified": Mode.MODE_UNSPECIFIED,
    Mode.MODE_DYNAMIC: Mode.MODE_DYNAMIC,
    1: Mode.MODE_DYNAMIC,
    "mode_dynamic": Mode.MODE_DYNAMIC,
    "dynamic": Mode.MODE_DYNAMIC,
}


def to_mode(x: ModeOptions) -> Mode:
    if isinstance(x, str):
        x = x.lower()
    return _MODE[x]


def _pil_to_blob(image: PIL.Image.Image) -> protos.Blob:
    # If the image is a local file, return a file-based blob without any modification.
    # Otherwise, return a lossless WebP blob (same quality with optimized size).
    def file_blob(image: PIL.Image.Image) -> protos.Blob | None:
        if not isinstance(image, PIL.ImageFile.ImageFile) or image.filename is None:
            return None
        filename = str(image.filename)
        if not pathlib.Path(filename).is_file():
            return None

        mime_type = image.get_format_mimetype()
        image_bytes = pathlib.Path(filename).read_bytes()

        return protos.Blob(mime_type=mime_type, data=image_bytes)

    def webp_blob(image: PIL.Image.Image) -> protos.Blob:
        # Reference: https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html#webp
        image_io = io.BytesIO()
        image.save(image_io, format="webp", lossless=True)
        image_io.seek(0)

        mime_type = "image/webp"
        image_bytes = image_io.read()

        return protos.Blob(mime_type=mime_type, data=image_bytes)

    return file_blob(image) or webp_blob(image)


def image_to_blob(image) -> protos.Blob:
    if PIL is not None:
        if isinstance(image, PIL.Image.Image):
            return _pil_to_blob(image)

    if IPython is not None:
        if isinstance(image, IPython.display.Image):
            name = image.filename
            if name is None:
                raise ValueError(
                    "Conversion failed. The `IPython.display.Image` can only be converted if "
                    "it is constructed from a local file. Please ensure you are using the format: Image(filename='...')."
                )
            mime_type, _ = mimetypes.guess_type(name)
            if mime_type is None:
                mime_type = "image/unknown"

            return protos.Blob(mime_type=mime_type, data=image.data)

    raise TypeError(
        "Image conversion failed. The input was expected to be of type `Image` "
        "(either `PIL.Image.Image` or `IPython.display.Image`).\n"
        f"However, received an object of type: {type(image)}.\n"
        f"Object Value: {image}"
    )


class BlobDict(TypedDict):
    mime_type: str
    data: bytes


def _convert_dict(d: Mapping) -> protos.Content | protos.Part | protos.Blob:
    if is_content_dict(d):
        content = dict(d)
        if isinstance(parts := content["parts"], str):
            content["parts"] = [parts]
        content["parts"] = [to_part(part) for part in content["parts"]]
        return protos.Content(content)
    elif is_part_dict(d):
        part = dict(d)
        if "inline_data" in part:
            part["inline_data"] = to_blob(part["inline_data"])
        if "file_data" in part:
            part["file_data"] = file_types.to_file_data(part["file_data"])
        return protos.Part(part)
    elif is_blob_dict(d):
        blob = d
        return protos.Blob(blob)
    else:
        raise KeyError(
            "Unable to determine the intended type of the `dict`. "
            "For `Content`, a 'parts' key is expected. "
            "For `Part`, either an 'inline_data' or a 'text' key is expected. "
            "For `Blob`, both 'mime_type' and 'data' keys are expected. "
            f"However, the provided dictionary has the following keys: {list(d.keys())}"
        )


def is_blob_dict(d):
    return "mime_type" in d and "data" in d


if typing.TYPE_CHECKING:
    BlobType = Union[
        protos.Blob, BlobDict, PIL.Image.Image, IPython.display.Image
    ]  # Any for the images
else:
    BlobType = Union[protos.Blob, BlobDict, Any]


def to_blob(blob: BlobType) -> protos.Blob:
    if isinstance(blob, Mapping):
        blob = _convert_dict(blob)

    if isinstance(blob, protos.Blob):
        return blob
    elif isinstance(blob, IMAGE_TYPES):
        return image_to_blob(blob)
    else:
        if isinstance(blob, Mapping):
            raise KeyError(
                "Could not recognize the intended type of the `dict`\n" "A content should have "
            )
        raise TypeError(
            "Could not create `Blob`, expected `Blob`, `dict` or an `Image` type"
            "(`PIL.Image.Image` or `IPython.display.Image`).\n"
            f"Got a: {type(blob)}\n"
            f"Value: {blob}"
        )


class PartDict(TypedDict):
    text: str
    inline_data: BlobType


# When you need a `Part` accept a part object, part-dict, blob or string
PartType = Union[
    protos.Part,
    PartDict,
    BlobType,
    str,
    protos.FunctionCall,
    protos.FunctionResponse,
    file_types.FileDataType,
]


def is_part_dict(d):
    keys = list(d.keys())
    if len(keys) != 1:
        return False

    key = keys[0]

    return key in ["text", "inline_data", "function_call", "function_response", "file_data"]


def to_part(part: PartType):
    if isinstance(part, Mapping):
        part = _convert_dict(part)

    if isinstance(part, protos.Part):
        return part
    elif isinstance(part, str):
        return protos.Part(text=part)
    elif isinstance(part, protos.FileData):
        return protos.Part(file_data=part)
    elif isinstance(part, (protos.File, file_types.File)):
        return protos.Part(file_data=file_types.to_file_data(part))
    elif isinstance(part, protos.FunctionCall):
        return protos.Part(function_call=part)
    elif isinstance(part, protos.FunctionResponse):
        return protos.Part(function_response=part)

    else:
        # Maybe it can be turned into a blob?
        return protos.Part(inline_data=to_blob(part))


class ContentDict(TypedDict):
    parts: list[PartType]
    role: str


def is_content_dict(d):
    return "parts" in d


# When you need a message accept a `Content` object or dict, a list of parts,
# or a single part
ContentType = Union[protos.Content, ContentDict, Iterable[PartType], PartType]

# For generate_content, we're not guessing roles for [[parts],[parts],[parts]] yet.
StrictContentType = Union[protos.Content, ContentDict]


def to_content(content: ContentType):
    if not content:
        raise ValueError(
            "Invalid input: 'content' argument must not be empty. Please provide a non-empty value."
        )

    if isinstance(content, Mapping):
        content = _convert_dict(content)

    if isinstance(content, protos.Content):
        return content
    elif isinstance(content, Iterable) and not isinstance(content, str):
        return protos.Content(parts=[to_part(part) for part in content])
    else:
        # Maybe this is a Part?
        return protos.Content(parts=[to_part(content)])


def strict_to_content(content: StrictContentType):
    if isinstance(content, Mapping):
        content = _convert_dict(content)

    if isinstance(content, protos.Content):
        return content
    else:
        raise TypeError(
            "Invalid input type. Expected a `protos.Content` or a `dict` with a 'parts' key.\n"
            f"However, received an object of type: {type(content)}.\n"
            f"Object Value: {content}"
        )


ContentsType = Union[ContentType, Iterable[StrictContentType], None]


def to_contents(contents: ContentsType) -> list[protos.Content]:
    if contents is None:
        return []

    if isinstance(contents, Iterable) and not isinstance(contents, (str, Mapping)):
        try:
            # strict_to_content so [[parts], [parts]] doesn't assume roles.
            contents = [strict_to_content(c) for c in contents]
            return contents
        except TypeError:
            # If you get a TypeError here it's probably because that was a list
            # of parts, not a list of contents, so fall back to `to_content`.
            pass

    contents = [to_content(contents)]
    return contents


def _schema_for_class(cls: TypedDict) -> dict[str, Any]:
    schema = _build_schema("dummy", {"dummy": (cls, pydantic.Field())})
    return schema["properties"]["dummy"]


def _schema_for_function(
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
    defaults = dict(inspect.signature(f).parameters)

    fields_dict = {}
    for name, param in defaults.items():
        if param.kind in (
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.KEYWORD_ONLY,
            inspect.Parameter.POSITIONAL_ONLY,
        ):
            # We do not support default values for now.
            # default=(
            #     param.default if param.default != inspect.Parameter.empty
            #     else None
            # ),
            field = pydantic.Field(
                # We support user-provided descriptions.
                description=descriptions.get(name, None)
            )

            # 1. We infer the argument type here: use Any rather than None so
            # it will not try to auto-infer the type based on the default value.
            if param.annotation != inspect.Parameter.empty:
                fields_dict[name] = param.annotation, field
            else:
                fields_dict[name] = Any, field

    parameters = _build_schema(f.__name__, fields_dict)

    # 6. Annotate required fields.
    if required is not None:
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
    schema = dict(name=f.__name__, description=f.__doc__)
    if parameters["properties"]:
        schema["parameters"] = parameters

    return schema


def _build_schema(fname, fields_dict):
    parameters = pydantic.create_model(fname, **fields_dict).model_json_schema()
    defs = parameters.pop("$defs", {})
    # flatten the defs
    for name, value in defs.items():
        unpack_defs(value, defs)
    unpack_defs(parameters, defs)

    # 5. Nullable fields:
    #     * https://github.com/pydantic/pydantic/issues/1270
    #     * https://stackoverflow.com/a/58841311
    #     * https://github.com/pydantic/pydantic/discussions/4872
    convert_to_nullable(parameters)
    add_object_type(parameters)
    # Postprocessing
    # 4. Suppress unnecessary title generation:
    #    * https://github.com/pydantic/pydantic/issues/1051
    #    * http://cl/586221780
    strip_titles(parameters)
    return parameters


def unpack_defs(schema, defs):
    properties = schema.get("properties", None)
    if properties is None:
        return

    for name, value in properties.items():
        ref_key = value.get("$ref", None)
        if ref_key is not None:
            ref = defs[ref_key.split("defs/")[-1]]
            unpack_defs(ref, defs)
            properties[name] = ref
            continue

        anyof = value.get("anyOf", None)
        if anyof is not None:
            for i, atype in enumerate(anyof):
                ref_key = atype.get("$ref", None)
                if ref_key is not None:
                    ref = defs[ref_key.split("defs/")[-1]]
                    unpack_defs(ref, defs)
                    anyof[i] = ref
            continue

        items = value.get("items", None)
        if items is not None:
            ref_key = items.get("$ref", None)
            if ref_key is not None:
                ref = defs[ref_key.split("defs/")[-1]]
                unpack_defs(ref, defs)
                value["items"] = ref
                continue


def strip_titles(schema):
    title = schema.pop("title", None)

    properties = schema.get("properties", None)
    if properties is not None:
        for name, value in properties.items():
            strip_titles(value)

    items = schema.get("items", None)
    if items is not None:
        strip_titles(items)


def add_object_type(schema):
    properties = schema.get("properties", None)
    if properties is not None:
        schema.pop("required", None)
        schema["type"] = "object"
        for name, value in properties.items():
            add_object_type(value)

    items = schema.get("items", None)
    if items is not None:
        add_object_type(items)


def convert_to_nullable(schema):
    anyof = schema.pop("anyOf", None)
    if anyof is not None:
        if len(anyof) != 2:
            raise ValueError(
                "Invalid input: Type Unions are not supported, except for `Optional` types. "
                "Please provide an `Optional` type or a non-Union type."
            )
        a, b = anyof
        if a == {"type": "null"}:
            schema.update(b)
        elif b == {"type": "null"}:
            schema.update(a)
        else:
            raise ValueError(
                "Invalid input: Type Unions are not supported, except for `Optional` types. "
                "Please provide an `Optional` type or a non-Union type."
            )
        schema["nullable"] = True

    properties = schema.get("properties", None)
    if properties is not None:
        for name, value in properties.items():
            convert_to_nullable(value)

    items = schema.get("items", None)
    if items is not None:
        convert_to_nullable(items)


def _rename_schema_fields(schema):
    if schema is None:
        return schema

    schema = schema.copy()

    type_ = schema.pop("type", None)
    if type_ is not None:
        schema["type_"] = type_.upper()

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

        schema = _schema_for_function(function, descriptions=descriptions)

        return CallableFunctionDeclaration(**schema, function=function)


StructType = dict[str, "ValueType"]
ValueType = Union[float, str, bool, StructType, list["ValueType"], None]


class CallableFunctionDeclaration(FunctionDeclaration):
    """An extension of `FunctionDeclaration` that can be built from a python function, and is callable.

    Note: The python function must have type annotations.
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
            "Invalid input type. Expected an instance of `genai.FunctionDeclarationType`.\n"
            f"However, received an object of type: {type(fun)}.\n"
            f"Object Value: {fun}"
        )


def _encode_fd(fd: FunctionDeclaration | protos.FunctionDeclaration) -> protos.FunctionDeclaration:
    if isinstance(fd, protos.FunctionDeclaration):
        return fd

    return fd.to_proto()


class DynamicRetrievalConfigDict(TypedDict):
    mode: protos.DynamicRetrievalConfig.mode
    dynamic_threshold: float


DynamicRetrievalConfig = Union[protos.DynamicRetrievalConfig, DynamicRetrievalConfigDict]


class GoogleSearchRetrievalDict(TypedDict):
    dynamic_retrieval_config: DynamicRetrievalConfig


GoogleSearchRetrievalType = Union[protos.GoogleSearchRetrieval, GoogleSearchRetrievalDict]


def _make_google_search_retrieval(gsr: GoogleSearchRetrievalType):
    if isinstance(gsr, protos.GoogleSearchRetrieval):
        return gsr
    elif isinstance(gsr, Mapping):
        drc = gsr.get("dynamic_retrieval_config", None)
        if drc is not None and isinstance(drc, Mapping):
            mode = drc.get("mode", None)
            if mode is not None:
                mode = to_mode(mode)
                gsr = gsr.copy()
                gsr["dynamic_retrieval_config"]["mode"] = mode
        return protos.GoogleSearchRetrieval(gsr)
    else:
        raise TypeError(
            "Invalid input type. Expected an instance of `genai.GoogleSearchRetrieval`.\n"
            f"However, received an object of type: {type(gsr)}.\n"
            f"Object Value: {gsr}"
        )


class Tool:
    """A wrapper for `protos.Tool`, Contains a collection of related `FunctionDeclaration` objects,
    protos.CodeExecution object, and protos.GoogleSearchRetrieval object."""

    def __init__(
        self,
        *,
        function_declarations: Iterable[FunctionDeclarationType] | None = None,
        google_search_retrieval: GoogleSearchRetrievalType | None = None,
        code_execution: protos.CodeExecution | None = None,
    ):
        # The main path doesn't use this but is seems useful.
        if function_declarations is not None:
            self._function_declarations = [
                _make_function_declaration(f) for f in function_declarations
            ]
            self._index = {}
            for fd in self._function_declarations:
                name = fd.name
                if name in self._index:
                    raise ValueError("")
                self._index[fd.name] = fd
        else:
            # Consistent fields
            self._function_declarations = []
            self._index = {}

        if google_search_retrieval is not None:
            self._google_search_retrieval = _make_google_search_retrieval(google_search_retrieval)
        else:
            self._google_search_retrieval = None

        self._proto = protos.Tool(
            function_declarations=[_encode_fd(fd) for fd in self._function_declarations],
            google_search_retrieval=google_search_retrieval,
            code_execution=code_execution,
        )

    @property
    def function_declarations(self) -> list[FunctionDeclaration | protos.FunctionDeclaration]:
        return self._function_declarations

    @property
    def google_search_retrieval(self) -> protos.GoogleSearchRetrieval:
        return self._google_search_retrieval

    @property
    def code_execution(self) -> protos.CodeExecution:
        return self._proto.code_execution

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
    str, Tool, protos.Tool, ToolDict, Iterable[FunctionDeclarationType], FunctionDeclarationType
]


def _make_tool(tool: ToolType) -> Tool:
    if isinstance(tool, Tool):
        return tool
    elif isinstance(tool, protos.Tool):
        if "code_execution" in tool:
            code_execution = tool.code_execution
        else:
            code_execution = None

        if "google_search_retrieval" in tool:
            google_search_retrieval = tool.google_search_retrieval
        else:
            google_search_retrieval = None

        return Tool(
            function_declarations=tool.function_declarations,
            google_search_retrieval=google_search_retrieval,
            code_execution=code_execution,
        )
    elif isinstance(tool, dict):
        if (
            "function_declarations" in tool
            or "google_search_retrieval" in tool
            or "code_execution" in tool
        ):
            return Tool(**tool)
        else:
            fd = tool
            return Tool(function_declarations=[protos.FunctionDeclaration(**fd)])
    elif isinstance(tool, str):
        if tool.lower() == "code_execution":
            return Tool(code_execution=protos.CodeExecution())
        # Check to see if one of the mode enums matches
        elif tool.lower() == "google_search_retrieval":
            return Tool(google_search_retrieval=protos.GoogleSearchRetrieval())
        else:
            raise ValueError(
                "The only string that can be passed as a tool is 'code_execution', or one of the specified values for the `mode` parameter for google_search_retrieval."
            )
    elif isinstance(tool, protos.CodeExecution):
        return Tool(code_execution=tool)
    elif isinstance(tool, protos.GoogleSearchRetrieval):
        return Tool(google_search_retrieval=tool)
    elif isinstance(tool, Iterable):
        return Tool(function_declarations=tool)
    else:
        try:
            return Tool(function_declarations=[tool])
        except Exception as e:
            raise TypeError(
                "Invalid input type. Expected an instance of `genai.ToolType`.\n"
                f"However, received an object of type: {type(tool)}.\n"
                f"Object Value: {tool}"
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
                        f"Invalid operation: A `FunctionDeclaration` named '{name}' is already defined. "
                        "Each `FunctionDeclaration` must have a unique name. Please use a different name."
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
    if isinstance(tools, str):
        if tools.lower() == "code_execution" or tools.lower() == "google_search_retrieval":
            return [_make_tool(tools)]
        else:
            raise ValueError("The only string that can be passed as a tool is 'code_execution'.")
    elif isinstance(tools, Iterable) and not isinstance(tools, Mapping):
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
            "Invalid input type. Failed to convert input to `protos.FunctionCallingConfig`.\n"
            f"Received an object of type: {type(obj)}.\n"
            f"Object Value: {obj}"
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
            "Invalid input type. Failed to convert input to `protos.ToolConfig`.\n"
            f"Received an object of type: {type(obj)}.\n"
            f"Object Value: {obj}"
        )
