"""A TypeError raised inside a custom steps function must not re-invoke it."""

import pytest

from agno.workflow import Workflow


def test_sync_body_type_error_propagates_and_runs_once():
    """str + int inside the function is a body bug, not a signature mismatch."""
    calls = []

    def checkout(workflow=None, execution_input=None):
        calls.append("call")
        if execution_input is None:
            return "Nothing to check out"
        return "Total: " + 42

    workflow = Workflow(name="checkout", steps=checkout)

    with pytest.raises(TypeError):
        workflow.run("order-123")

    assert len(calls) == 1


@pytest.mark.asyncio
async def test_async_body_type_error_propagates_and_runs_once():
    """len(None) inside an async steps function runs it once, then raises."""
    calls = []

    async def acheckout(workflow, execution_input):
        calls.append("call")
        return len(None)

    workflow = Workflow(name="acheckout", steps=acheckout)

    with pytest.raises(TypeError):
        await workflow.arun("order-456")

    assert len(calls) == 1
