import hashlib
import json
import re
from typing import Optional, Dict, Any, Tuple

from phi.utils.log import logger


def hash_string_sha256(input_string):
    # Encode the input string to bytes
    encoded_string = input_string.encode("utf-8")

    # Create a SHA-256 hash object
    sha256_hash = hashlib.sha256()

    # Update the hash object with the encoded string
    sha256_hash.update(encoded_string)

    # Get the hexadecimal digest of the hash
    hex_digest = sha256_hash.hexdigest()

    return hex_digest


def extract_valid_json(content: str) -> Tuple[Optional[Dict[str, Any]], str]:
    """
    Extract the first valid JSON object from a string and return the JSON object
    along with the rest of the string without the JSON.

    Args:
        content (str): The input string containing potential JSON data.

    Returns:
        Tuple[Optional[Dict[str, Any]], str]:
            - Extracted JSON dictionary if valid, else None.
            - The rest of the string without the extracted JSON.
    """
    json_pattern = r'\{.*?\}'
    matches = re.finditer(json_pattern, content, re.DOTALL)

    for match in matches:
        try:
            # Attempt to load the matched string as JSON
            json_obj = json.loads(match.group())
            if isinstance(json_obj, dict):  # Ensure it's a JSON object
                # Remove the matched JSON object from the string
                remaining_content = content[:match.start()] + content[match.end():]
                return json_obj, remaining_content.strip()
        except json.JSONDecodeError:
            continue  # Skip invalid JSON matches

    # If no valid JSON is found, return None and the original string
    return None, content
