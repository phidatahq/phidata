from typing import Any, Dict, List


def merge_dictionaries(a: Dict[str, Any], b: Dict[str, Any]) -> None:
    """
    Recursively merges two dictionaries.
    If there are conflicting keys, values from 'b' will take precedence.

    Args:
        a (Dict[str, Any]): The first dictionary to be merged.
        b (Dict[str, Any]): The second dictionary, whose values will take precedence.

    Returns:
        None: The function modifies the first dictionary in place.
    """
    for key in b:
        if key in a and isinstance(a[key], dict) and isinstance(b[key], dict):
            merge_dictionaries(a[key], b[key])
        else:
            a[key] = b[key]


def _collect_state_changes(original_state: Dict[str, Any], modified_state: Dict[str, Any], changes: Dict[str, Any]) -> None:
    """
    Deep-diffs one branch's state against the original, recording only keys (or
    nested keys) whose value actually changed into ``changes``. Recursing keeps
    a branch's stale copy of an unchanged nested dict from entering the
    change-set and clobbering another branch's write to it.
    """
    for key, value in modified_state.items():
        if key not in original_state:
            changes[key] = value
        elif isinstance(original_state[key], dict) and isinstance(value, dict):
            existing = changes.get(key)
            sub_changes = existing if isinstance(existing, dict) else {}
            _collect_state_changes(original_state[key], value, sub_changes)
            changes[key] = sub_changes
        elif original_state[key] != value:
            changes[key] = value


def merge_parallel_session_states(original_state: Dict[str, Any], modified_states: List[Dict[str, Any]]) -> None:
    """
    Smart merge for parallel session states that only applies actual changes.
    This prevents parallel steps from overwriting each other's changes.

    Changes are deep-diffed per branch against the original state, so two
    branches that touched different nested keys of the same top-level dict both
    survive the merge regardless of completion order; scalar conflicts keep
    last-write-wins ordering.
    """
    if original_state is None or not modified_states:
        return

    changes: Dict[str, Any] = {}
    for modified_state in modified_states:
        if not modified_state:
            continue
        _collect_state_changes(original_state, modified_state, changes)

    for key, value in changes.items():
        if key in original_state and isinstance(original_state[key], dict) and isinstance(value, dict):
            merge_dictionaries(original_state[key], value)
        else:
            original_state[key] = value
