from typing import List, Dict, Any


def get_function_names_from_tool_calls(tool_calls: List[Dict[str, Any]]) -> List[str]:
    _f_names = []
    for tool_call in tool_calls:
        _function = tool_call.get("function")
        _function_name = _function.get("name")
        _function_arguments_str = _function.get("arguments")
        if _function_name:
            _f_names.append(_function_name)
    return _f_names
