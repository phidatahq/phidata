from .core import (
    infer_vegalite_type,
    infer_encoding_types,
    sanitize_dataframe,
    sanitize_arrow_table,
    parse_shorthand,
    use_signature,
    update_nested,
    display_traceback,
    SchemaBase,
)
from .html import spec_to_html
from .plugin_registry import PluginRegistry
from .deprecation import AltairDeprecationWarning
from .schemapi import Undefined


__all__ = (
    "infer_vegalite_type",
    "infer_encoding_types",
    "sanitize_dataframe",
    "sanitize_arrow_table",
    "spec_to_html",
    "parse_shorthand",
    "use_signature",
    "update_nested",
    "display_traceback",
    "AltairDeprecationWarning",
    "SchemaBase",
    "Undefined",
    "PluginRegistry",
)
