from typing import Any, Dict, Union, get_args, get_origin, Optional

from phi.utils.log import logger


def get_json_type_for_py_type(arg: str) -> str:
    """
    Get the JSON schema type for a given type.
    :param arg: The type to get the JSON schema type for.
    :return: The JSON schema type.

    See: https://json-schema.org/understanding-json-schema/reference/type.html#type-specific-keywords
    """
    # logger.info(f"Getting JSON type for: {arg}")
    if arg in ("int", "float"):
        return "number"
    elif arg == "str":
        return "string"
    elif arg == "bool":
        return "boolean"
    elif arg in ("NoneType", "None"):
        return "null"
    return arg


def get_json_schema_for_arg(t: Any) -> Optional[Any]:
    # logger.info(f"Getting JSON schema for arg: {t}")
    json_schema = None
    type_args = get_args(t)
    # logger.info(f"Type args: {type_args}")
    type_origin = get_origin(t)
    # logger.info(f"Type origin: {type_origin}")
    if type_origin is not None:
        if type_origin == list:
            json_schema_for_items = get_json_schema_for_arg(type_args[0])
            json_schema = {"type": "array", "items": json_schema_for_items}
        elif type_origin == dict:
            json_schema = {"type": "object", "properties": {}}
        elif type_origin == Union:
            json_schema = {"type": [get_json_type_for_py_type(arg.__name__) for arg in type_args]}
    else:
        json_schema = {"type": get_json_type_for_py_type(t.__name__)}
    return json_schema


def get_json_schema(type_hints: Dict[str, Any]) -> Dict[str, Any]:
    json_schema: Dict[str, Any] = {"type": "object", "properties": {}}
    for k, v in type_hints.items():
        # logger.info(f"Parsing arg: {k} | {v}")
        if k == "return":
            continue
        arg_json_schema = get_json_schema_for_arg(v)
        if arg_json_schema is not None:
            # logger.info(f"json_schema: {arg_json_schema}")
            json_schema["properties"][k] = arg_json_schema
        else:
            logger.warning(f"Could not parse argument {k} of type {v}")
    return json_schema
