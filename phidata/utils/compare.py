from typing import Any, List, Optional


def compare_dicts(
    dict1: Any,
    dict2: Any,
    ignore_keys: Optional[List[str]] = None,
    compare_keys_only_in_dict1: bool = True,
) -> bool:
    """Compares two dictionaries and returns True if they are equal.

    Args:
        dict1: The first dictionary to compare
        dict2: The second dictionary to compare
        ignore_keys: A list of keys to ignore when comparing the dictionaries
        compare_keys_only_in_dict1: If True, only keys in dict1 will be compared

    Returns:
        True if the dictionaries are equal, False otherwise
    """
    if not (isinstance(dict1, dict) and isinstance(dict2, dict)):
        return False

    # Remove ignored keys from the dictionaries
    if ignore_keys:
        for key in ignore_keys:
            dict1.pop(key, None)
            dict2.pop(key, None)

    # Compare the dictionaries
    if compare_keys_only_in_dict1:
        return dict1 == {k: dict2[k] for k in dict1 if k in dict2}
    else:
        return dict1 == dict2
