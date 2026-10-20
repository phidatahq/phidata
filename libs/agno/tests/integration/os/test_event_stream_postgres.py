"""PostgresEventStream against a real Postgres: the in-memory stream's contract, cross-process."""

import asyncio
import os
from uuid import uuid4

import pytest
import pytest_asyncio

from agno.os.event_streams.postgres import PostgresEventStream
from agno.run.agent import RunContentEvent
from agno.run.base import RunStatus

URL = os.environ.get("AGNO_TEST_SANDBOX_DB_URL") or os.environ.get("AGNO_TEST_PG_URL")
pytestmark = [pytest.mark.asyncio, pytest.mark.skipif(not URL, reason="Set AGNO_TEST_SANDBOX_DB_URL for Postgres")]


@pytest_asyncio.fixture
async def stream():
    s = PostgresEventStream(URL, table_prefix="test_events_" + uuid4().hex[:8], poll_seconds=0.05)
    yield s
    await asyncio.to_thread(s._execute, f"DROP TABLE IF EXISTS {s.events_table}")
    await asyncio.to_thread(s._execute, f"DROP TABLE IF EXISTS {s.runs_table}")
    await s.aclose()


def make_event(run_id: str, content: str) -> RunContentEvent:
    return RunContentEvent(content=content, run_id=run_id)


async def test_register_and_status_transitions(stream):
    await stream.register_run("r1")
    assert await stream.get_run_status("r1") == RunStatus.pending
    await stream.set_run_status("r1", RunStatus.running)
    assert await stream.get_run_status("r1") == RunStatus.running
    await stream.complete_run("r1", RunStatus.completed)
    assert await stream.get_run_status("r1") == RunStatus.completed
    await stream.register_run("r1")  # idempotent: does not reset
    assert await stream.get_run_status("r1") == RunStatus.completed
    assert await stream.get_run_status("unknown") is None
    await stream.cleanup_run("r1")
    assert await stream.get_run_status("r1") is None


async def test_indices_are_monotonic_and_replay_from_index(stream):
    await stream.register_run("r1", RunStatus.running)
    indices = [await stream.add_event("r1", make_event("r1", c)) for c in "abc"]
    assert indices == [0, 1, 2]
    assert await stream.get_last_index("r1") == 2
    assert await stream.get_event_count("r1") == 3
    assert [i for i, _ in await stream.replay("r1")] == [0, 1, 2]
    replayed = await stream.replay("r1", last_event_index=0)
    assert [i for i, _ in replayed] == [1, 2]
    assert all("event_index" in sse for _, sse in replayed)


async def test_tail_replays_then_streams_live_without_dups(stream):
    await stream.register_run("r1", RunStatus.running)
    await stream.add_event("r1", make_event("r1", "a"))
    await stream.add_event("r1", make_event("r1", "b"))
    received: list = []
    done = asyncio.Event()

    async def consume():
        async for idx, _sse in stream.tail("r1"):
            received.append(idx)
        done.set()

    consumer = asyncio.create_task(consume())
    await asyncio.sleep(0.2)
    await stream.add_event("r1", make_event("r1", "c"))
    await asyncio.sleep(0.2)
    await stream.complete_run("r1", RunStatus.completed)
    await asyncio.wait_for(done.wait(), timeout=5)
    assert received == [0, 1, 2]
    await consumer


async def test_tail_resumes_after_last_event_index_and_ends_on_completed_run(stream):
    await stream.register_run("r1", RunStatus.running)
    for content in "abc":
        await stream.add_event("r1", make_event("r1", content))
    await stream.complete_run("r1", RunStatus.completed)
    assert [idx async for idx, _ in stream.tail("r1", last_event_index=0)] == [1, 2]
    assert [idx async for idx, _ in stream.tail("r1")] == [0, 1, 2]


async def test_tail_ends_when_run_completes_with_no_events_and_for_unknown_runs(stream):
    await stream.register_run("r1", RunStatus.running)
    received: list = []
    done = asyncio.Event()

    async def consume():
        async for idx, _ in stream.tail("r1"):
            received.append(idx)
        done.set()

    consumer = asyncio.create_task(consume())
    await asyncio.sleep(0.2)
    await stream.complete_run("r1", RunStatus.cancelled)
    await asyncio.wait_for(done.wait(), timeout=5)
    assert received == []
    await consumer
    assert [idx async for idx, _ in stream.tail("never-registered")] == []


async def test_another_process_sees_the_same_stream(stream):
    """Two stream objects with separate engines, as two replicas would have."""
    other = PostgresEventStream(
        URL, table_prefix=stream.runs_table.split('"')[3].removesuffix("_runs"), poll_seconds=0.05
    )
    try:
        await stream.register_run("r1", RunStatus.running)
        received: list = []
        done = asyncio.Event()

        async def consume():
            async for idx, _ in other.tail("r1"):
                received.append(idx)
            done.set()

        consumer = asyncio.create_task(consume())
        for content in "abc":
            await stream.add_event("r1", make_event("r1", content))
            await asyncio.sleep(0.1)
        await stream.complete_run("r1", RunStatus.completed)
        await asyncio.wait_for(done.wait(), timeout=5)
        assert received == [0, 1, 2]
        await consumer
    finally:
        await other.aclose()


async def test_generation_fence_refuses_older_writers_and_heals_forward(stream):
    await stream.register_run("r1", RunStatus.running)
    await stream.begin_attempt("r1", 2)
    assert await stream.add_event("r1", make_event("r1", "live"), generation=2) == 0
    assert await stream.add_event("r1", make_event("r1", "zombie"), generation=1) == -1
    assert await stream.add_event("r1", make_event("r1", "newer"), generation=3) == 1
    await stream.complete_run("r1", RunStatus.completed, generation=1)  # a zombie's sentinel is ignored
    assert await stream.get_run_status("r1") == RunStatus.running
    await stream.complete_run("r1", RunStatus.completed, generation=3)
    assert await stream.get_run_status("r1") == RunStatus.completed
    await stream.begin_attempt("r1", 1)  # a late older begin never regresses the generation
    assert await stream.add_event("r1", make_event("r1", "late"), generation=1) == -1


async def test_reset_keeps_the_counter_and_reopen_seeds_the_floor(stream):
    await stream.register_run("r1", RunStatus.running)
    for content in "ab":
        await stream.add_event("r1", make_event("r1", content))
    await stream.reset_run_events("r1")
    assert await stream.get_event_count("r1") == 0
    assert await stream.add_event("r1", make_event("r1", "retry")) == 2, "indices stay monotonic across attempts"

    await stream.complete_run("r1", RunStatus.paused)
    assert await stream.reopen_run("r1", floor=10) is True
    assert await stream.get_run_status("r1") == RunStatus.pending
    assert await stream.add_event("r1", make_event("r1", "after approval")) == 11
    await stream.complete_run("r1", RunStatus.completed)
    assert await stream.reopen_run("r1") is False, "a finished run is never reopened"
    assert await stream.reopen_run("expired", floor=4) is True, "an unknown run reopens with the seeded counter"
    assert await stream.add_event("expired", make_event("expired", "x")) == 5
