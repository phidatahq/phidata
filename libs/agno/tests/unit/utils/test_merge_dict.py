"""Regression tests for merge_parallel_session_states (issue #11257)."""

import pytest

from agno.utils.merge_dict import merge_parallel_session_states


def test_nested_changes_from_parallel_branches_both_survive():
    original = {"cart": {"items": 1}}
    a = {"cart": {"items": 1, "coupon": "X"}}
    b = {"cart": {"items": 2}}

    merge_parallel_session_states(original, [a, b])

    assert original["cart"]["items"] == 2
    assert original["cart"]["coupon"] == "X"


def test_empty_initial_state_keeps_parallel_writes():
    state = {}
    merge_parallel_session_states(state, [{"result": "done"}])

    assert state == {"result": "done"}


def test_result_is_order_independent():
    a = {"cart": {"items": 1, "coupon": "X"}}
    b = {"cart": {"items": 2}}

    one = {"cart": {"items": 1}}
    merge_parallel_session_states(one, [a, b])
    two = {"cart": {"items": 1}}
    merge_parallel_session_states(two, [b, a])

    assert one == two == {"cart": {"items": 2, "coupon": "X"}}


def test_unchanged_branch_does_not_revert_other_branch():
    original = {"cart": {"items": 1}}
    unchanged = {"cart": {"items": 1}}
    updated = {"cart": {"items": 2, "coupon": "Y"}}

    merge_parallel_session_states(original, [unchanged, updated])

    assert original["cart"] == {"items": 2, "coupon": "Y"}


def test_different_top_level_keys_merge():
    original = {"a": 1}
    merge_parallel_session_states(original, [{"b": 2}, {"c": 3}])

    assert original == {"a": 1, "b": 2, "c": 3}


def test_scalar_conflict_keeps_last_write_wins():
    original = {"count": 1}
    merge_parallel_session_states(original, [{"count": 5}, {"count": 9}])

    assert original["count"] == 9


def test_non_dict_value_replaces_instead_of_merging():
    original = {"tags": ["a"]}
    merge_parallel_session_states(original, [{"tags": ["a", "b"]}])

    assert original["tags"] == ["a", "b"]


def test_empty_modified_states_are_noop():
    original = {"a": 1}
    merge_parallel_session_states(original, [{}, None])

    assert original == {"a": 1}


@pytest.mark.parametrize("order", [[0, 1], [1, 0]])
def test_deeply_nested_keys_from_both_branches_survive(order):
    original = {"session": {"memory": {"facts": 1}, "summary": "s"}}
    x = {"session": {"memory": {"facts": 1, "entities": 3}}}
    y = {"session": {"memory": {"facts": 2}}}

    merge_parallel_session_states(original, [x, y] if order == [0, 1] else [y, x])

    assert original["session"]["memory"] == {"facts": 2, "entities": 3}
    assert original["session"]["summary"] == "s"
