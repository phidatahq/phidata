import json
from typing import Optional, Dict, Literal, Union

from pydantic import BaseModel


class MessageToolCallExtractionResult(BaseModel):
    tool_calls: Optional[list] = None
    invalid_json_format: bool = False


def extract_json(s: str) -> Union[Optional[Dict], Literal[False]]:
    """
    Extracts all valid JSON from a string then combines them and returns it as a dictionary.

    Args:
        s: The string to extract JSON from.

    Returns:
        A dictionary containing the extracted JSON, or None if no JSON was found or False if an invalid JSON was found.
    """
    json_objects = []
    start_idx = 0

    while start_idx < len(s):
        # Find the next '{' which indicates the start of a JSON block
        json_start = s.find("{", start_idx)
        if json_start == -1:
            break  # No more JSON objects found

        # Find the matching '}' for the found '{'
        stack = []
        i = json_start
        while i < len(s):
            if s[i] == "{":
                stack.append("{")
            elif s[i] == "}":
                if stack:
                    stack.pop()
                    if not stack:
                        json_end = i
                        break
            i += 1
        else:
            return False

        json_str = s[json_start : json_end + 1]
        try:
            json_obj = json.loads(json_str)
            json_objects.append(json_obj)
        except ValueError:
            return False

        start_idx = json_end + 1

    if not json_objects:
        return None

    # Combine all JSON objects into one
    combined_json = {}
    for obj in json_objects:
        for key, value in obj.items():
            if key not in combined_json:
                combined_json[key] = value
            elif isinstance(value, list) and isinstance(combined_json[key], list):
                combined_json[key].extend(value)

    return combined_json


def extract_tool_calls(assistant_msg_content: str) -> MessageToolCallExtractionResult:
    json_obj = extract_json(assistant_msg_content)
    if json_obj is None:
        return MessageToolCallExtractionResult()

    if json_obj is False or not isinstance(json_obj, dict):
        return MessageToolCallExtractionResult(invalid_json_format=True)

    tool_calls: Optional[list] = json_obj.get("tool_calls")

    # Not tool call json object
    if not isinstance(tool_calls, list):
        return MessageToolCallExtractionResult(invalid_json_format=True)

    return MessageToolCallExtractionResult(tool_calls=tool_calls)
