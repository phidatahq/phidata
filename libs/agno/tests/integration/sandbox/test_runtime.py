"""Real runtime protocol acceptance without model calls. Requires a built runtime image."""

import asyncio
import os
from uuid import uuid4

import pytest
import pytest_asyncio

from agno.sandbox import SandboxSpec
from agno.sandbox.client import SandboxRuntimeClient
from agno.sandbox.docker import DockerSandboxProvider

IMAGE = os.environ.get("AGNO_TEST_RUNTIME_IMAGE")
pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.skipif(not IMAGE, reason="Set AGNO_TEST_RUNTIME_IMAGE after building the cookbook image"),
]


@pytest_asyncio.fixture
async def runtime_computer():
    provider = DockerSandboxProvider("runtime-test-" + uuid4().hex)
    handle = await provider.acreate(
        SandboxSpec("a", "s", 1, IMAGE, env={"AGNO_SANDBOX_TEST_RUNTIME": "1"}, memory_mb=512)
    )
    try:
        yield provider, handle, SandboxRuntimeClient(provider)
    finally:
        await provider.adestroy(handle)


async def test_reconnect_and_duplicate_dispatch_execute_only_once(runtime_computer):
    provider, computer, first = runtime_computer
    execution = await first.astart(
        computer, execution_id="e", run_id="r", sdk="fixture", input="hello", config={"delay": 0.3}
    )
    second = SandboxRuntimeClient(DockerSandboxProvider(provider.namespace))
    assert (
        await second.astart(computer, execution_id="e", run_id="r", sdk="fixture", input="hello", config={"delay": 0.3})
        == execution
    )
    pages = [page async for page in second.apages(execution, timeout=20)]
    assert pages[-1].result["type"] == "execution_finished"
    assert pages[-1].result["run"]["content"] == "hello"
    assert any(event["content"] == "hello" for page in pages for event in page.events)
    assert not any(event["event"] == "RunCompleted" for page in pages for event in page.events)
    replay = await first.apoll(execution, cursor=0)
    assert replay.events[0]["content"] == "hello"
    result = await provider.aexec(computer, ["cat", "fixture-effects.txt"])
    assert result.stdout == "r\n"


async def test_detached_polling_does_not_cancel_execution(runtime_computer):
    provider, computer, client = runtime_computer
    execution = await client.astart(
        computer, execution_id="e", run_id="r", sdk="fixture", input="late", config={"delay": 1}
    )
    with pytest.raises(TimeoutError, match="Detached"):
        await client.await_result(execution, timeout=0.01)
    result = await SandboxRuntimeClient(provider).await_result(execution, timeout=20)
    assert result["type"] == "execution_finished" and result["run"]["content"] == "late"
    assert (await provider.aget(computer.provider_ref)).state == "running"


async def test_runtime_cancel_stops_entire_computer(runtime_computer):
    provider, computer, client = runtime_computer
    execution = await client.astart(
        computer, execution_id="e", run_id="r", sdk="fixture", input="never", config={"delay": 30}
    )
    await client.acancel(execution)
    assert (await provider.aget(computer.provider_ref)).state == "exited"


async def test_runtime_rejects_overlapping_writer_without_repeating_first(runtime_computer):
    provider, computer, client = runtime_computer
    first = await client.astart(
        computer, execution_id="first", run_id="r", sdk="fixture", input="first", config={"delay": 2}
    )
    for _ in range(50):
        result = await provider.aexec(computer, ["test", "-f", "fixture-effects.txt"])
        if result.exit_code == 0:
            break
        await asyncio.sleep(0.01)
    second = await client.astart(computer, execution_id="second", run_id="r2", sdk="fixture", input="second")
    result = await client.await_result(second, timeout=20)
    assert result["type"] == "execution_error" and "already has a writer" in result["error"]
    assert (await client.await_result(first, timeout=20))["type"] == "execution_finished"
    assert (await provider.aexec(computer, ["cat", "fixture-effects.txt"])).stdout == "r\n"


async def test_binary_command_stdin_round_trip(runtime_computer):
    provider, computer, _ = runtime_computer
    payload = bytes(range(256)) * 4096
    result = await provider.aexec(
        computer,
        ["python", "-c", "import sys,hashlib; print(hashlib.sha256(sys.stdin.buffer.read()).hexdigest())"],
        stdin=payload,
    )
    import hashlib

    assert result.stdout.strip() == hashlib.sha256(payload).hexdigest()


async def test_dead_worker_reports_unknown_without_reexecution(runtime_computer):
    provider, computer, client = runtime_computer
    execution = await client.astart(
        computer, execution_id="e", run_id="r", sdk="fixture", input="lost", config={"delay": 30}
    )
    script = "import pathlib,json,os,signal; p=next(pathlib.Path('/runtime/jobs').glob('*/status.json')); s=json.loads(p.read_text()); os.kill(s['pid'], signal.SIGKILL)"
    for _ in range(50):
        result = await provider.aexec(computer, ["python", "-c", script])
        if result.exit_code == 0:
            break
        await asyncio.sleep(0.02)
    else:
        pytest.fail("Runtime worker did not start")
    result = await client.await_result(execution, timeout=20)
    assert result["type"] == "execution_unknown"
    await client.astart(computer, execution_id="e", run_id="r", sdk="fixture", input="lost", config={"delay": 30})
    assert (await provider.aexec(computer, ["cat", "fixture-effects.txt"])).stdout == "r\n"


async def test_installed_sdk_adapters_construct_without_model_calls(runtime_computer):
    provider, computer, _ = runtime_computer
    script = """
from pathlib import Path
from agno.sandbox.runtime import _agent
root = Path('/runtime/native')
root.mkdir()
claude = _agent({'sdk': 'claude', 'agent_id': 'a'}, root)
codex = _agent({'sdk': 'codex', 'agent_id': 'a'}, root)
assert claude.sdk == 'claude-agent-sdk' and codex.sdk == 'codex'
assert claude.cwd == codex.cwd == '/workspace'
assert claude.retries == codex.retries == 0
assert claude.db.db_engine.dialect.name == 'sqlite'
claude.db.db_engine.dispose()
codex.db.db_engine.dispose()
print('SDK construction passed without model calls')
"""
    result = await provider.aexec(computer, ["python", "-c", script])
    assert result.exit_code == 0, result.stderr
    assert "SDK construction passed" in result.stdout


async def test_lost_poll_response_keeps_execution_available_for_another_client(runtime_computer, monkeypatch):
    import json

    provider, computer, first = runtime_computer
    execution = await first.astart(
        computer, execution_id="e", run_id="r", sdk="fixture", input="survives", config={"delay": 1}
    )
    original = provider._docker
    lost = []

    async def lose_response(*args, **kwargs):
        response = await original(*args, **kwargs)
        if args[:2] == ("container", "exec") and kwargs.get("input_data"):
            command = json.loads(kwargs["input_data"])
            if command["argv"][-1] == "poll" and not lost:
                lost.append(True)
                raise TimeoutError("injected lost poll response")
        return response

    monkeypatch.setattr(provider, "_docker", lose_response)
    with pytest.raises(TimeoutError, match="lost poll"):
        await first.apoll(execution)
    assert (await provider.aget(computer.provider_ref)).state == "running"
    second = SandboxRuntimeClient(DockerSandboxProvider(provider.namespace))
    assert (await second.await_result(execution, timeout=20))["run"]["content"] == "survives"
    assert (await provider.aexec(computer, ["cat", "fixture-effects.txt"])).stdout == "r\n"
