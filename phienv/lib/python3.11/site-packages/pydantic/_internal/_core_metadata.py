from __future__ import annotations as _annotations

import typing
from typing import Any, cast

import typing_extensions

if typing.TYPE_CHECKING:
    from pydantic_core import CoreSchema

    from ._schema_generation_shared import (
        CoreSchemaOrField,
        GetJsonSchemaFunction,
    )


class CoreMetadata(typing_extensions.TypedDict, total=False):
    """A `TypedDict` for holding the metadata dict of the schema.

    Attributes:
        pydantic_js_functions: List of JSON schema functions.
        pydantic_js_prefer_positional_arguments: Whether JSON schema generator will
            prefer positional over keyword arguments for an 'arguments' schema.
    """

    pydantic_js_functions: list[GetJsonSchemaFunction]
    pydantic_js_annotation_functions: list[GetJsonSchemaFunction]

    # If `pydantic_js_prefer_positional_arguments` is True, the JSON schema generator will
    # prefer positional over keyword arguments for an 'arguments' schema.
    pydantic_js_prefer_positional_arguments: bool | None
    pydantic_js_input_core_schema: CoreSchema | None


class CoreMetadataHandler:
    """Because the metadata field in pydantic_core is of type `Dict[str, Any]`, we can't assume much about its contents.

    This class is used to interact with the metadata field on a CoreSchema object in a consistent way throughout pydantic.

    TODO: We'd like to refactor the storage of json related metadata to be more explicit, and less functionally oriented.
    This should make its way into our v2.10 release. It's inevitable that we need to store some json schema related information
    on core schemas, given that we generate JSON schemas directly from core schemas. That being said, debugging related
    issues is quite difficult when JSON schema information is disguised via dynamically defined functions.
    """

    __slots__ = ('_schema',)

    def __init__(self, schema: CoreSchemaOrField):
        self._schema = schema

        metadata = schema.get('metadata')
        if metadata is None:
            schema['metadata'] = CoreMetadata()  # type: ignore
        elif not isinstance(metadata, dict):
            raise TypeError(f'CoreSchema metadata should be a dict; got {metadata!r}.')

    @property
    def metadata(self) -> CoreMetadata:
        """Retrieves the metadata dict from the schema, initializing it to a dict if it is None
        and raises an error if it is not a dict.
        """
        metadata = self._schema.get('metadata')
        if metadata is None:
            self._schema['metadata'] = metadata = CoreMetadata()  # type: ignore
        if not isinstance(metadata, dict):
            raise TypeError(f'CoreSchema metadata should be a dict; got {metadata!r}.')
        return cast(CoreMetadata, metadata)


def build_metadata_dict(
    *,  # force keyword arguments to make it easier to modify this signature in a backwards-compatible way
    js_functions: list[GetJsonSchemaFunction] | None = None,
    js_annotation_functions: list[GetJsonSchemaFunction] | None = None,
    js_prefer_positional_arguments: bool | None = None,
    js_input_core_schema: CoreSchema | None = None,
) -> dict[str, Any]:
    """Builds a dict to use as the metadata field of a CoreSchema object in a manner that is consistent with the `CoreMetadataHandler` class."""
    metadata = CoreMetadata(
        pydantic_js_functions=js_functions or [],
        pydantic_js_annotation_functions=js_annotation_functions or [],
        pydantic_js_prefer_positional_arguments=js_prefer_positional_arguments,
        pydantic_js_input_core_schema=js_input_core_schema,
    )
    return {k: v for k, v in metadata.items() if v is not None}
