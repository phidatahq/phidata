"""Credential-free Docker acceptance. Set AGNO_TEST_DOCKER_IMAGE to opt in."""

import asyncio
import json
import os
from uuid import uuid4

import pytest
import pytest_asyncio

from agno.sandbox.base import SandboxError, SandboxSpec
from agno.sandbox.docker import DockerSandboxProvider

IMAGE = os.environ.get("AGNO_TEST_DOCKER_IMAGE")
pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.skipif(not IMAGE, reason="Set AGNO_TEST_DOCKER_IMAGE for real Docker tests"),
]


@pytest_asyncio.fixture
async def computer():
    provider = DockerSandboxProvider("test-" + uuid4().hex)
    spec = SandboxSpec("coder", "session", 1, IMAGE, memory_mb=256, workspace_mb=32, env={"EXPLICIT": "yes"})
    handle = await provider.acreate(spec)
    try:
        yield provider, spec, handle
    finally:
        await provider.adestroy(handle)


async def test_real_files_isolation_and_reuse(computer, monkeypatch):
    provider, spec, handle = computer
    monkeypatch.setenv("AGNO_DB_URL", "control-plane-secret")
    assert await provider.acreate(spec) == handle
    result = await provider.aexec(
        handle, ["python", "-c", "from pathlib import Path; Path('hello').write_text('world')"]
    )
    assert result.exit_code == 0
    result = await provider.aexec(handle, ["cat", "hello"])
    assert result.stdout == "world"
    result = await provider.aexec(
        handle,
        [
            "python",
            "-c",
            "import os,json; print(json.dumps([os.getuid(),os.getenv('EXPLICIT'),os.getenv('AGNO_DB_URL'),os.getenv('HOME')]))",
        ],
    )
    assert json.loads(result.stdout) == [1000, "yes", None, "/runtime"]
    result = await provider.aexec(handle, ["sh", "-c", "touch /root-file; test -S /var/run/docker.sock"])
    assert result.exit_code != 0 and "Read-only file system" in result.stderr
    _, out, _ = await provider._docker("container", "inspect", handle.provider_ref)
    config = json.loads(out)[0]["HostConfig"]
    assert config["NetworkMode"] == "none"
    assert config["ReadonlyRootfs"] and not config["Privileged"] and not config["Binds"]
    assert config["CapDrop"] == ["ALL"] and config["Memory"] == 256 * 1024**2
    assert "no-new-privileges" in config["SecurityOpt"]
    result = await provider.aexec(handle, ["sh", "-c", "echo error >&2; exit 7"])
    assert result.exit_code == 7 and result.stderr == "error\n"


async def test_real_timeout_stops_computer_and_prevents_reuse(computer):
    provider, spec, handle = computer
    result = await provider.aexec(handle, ["python", "-c", "import time; time.sleep(30)"], timeout=0.1)
    assert result.timed_out
    assert (await provider.aget(handle.provider_ref)).state == "exited"
    with pytest.raises(SandboxError, match="new generation"):
        await provider.acreate(spec)


async def test_real_output_limit_stops_computer(computer):
    provider, _, handle = computer
    result = await provider.aexec(handle, ["python", "-c", "print('x' * 1000000)"], max_output_bytes=100)
    assert result.output_limited and len(result.stdout) <= 100
    assert (await provider.aget(handle.provider_ref)).state == "exited"


async def test_real_cancel_stops_remote_children(computer):
    provider, _, handle = computer
    task = asyncio.create_task(provider.aexec(handle, ["sh", "-c", "touch started; sleep 30"], timeout=40))
    for _ in range(100):
        result = await provider.aexec(handle, ["test", "-f", "started"])
        if result.exit_code == 0:
            break
        await asyncio.sleep(0.02)
    else:
        pytest.fail("Remote process did not start")
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert (await provider.aget(handle.provider_ref)).state == "exited"


async def test_real_concurrent_creation_and_idempotent_delete():
    namespace = "test-" + uuid4().hex
    first, second = DockerSandboxProvider(namespace), DockerSandboxProvider(namespace)
    spec = SandboxSpec("coder", "concurrent", 1, IMAGE, memory_mb=256)
    handles = await asyncio.gather(first.acreate(spec), second.acreate(spec), return_exceptions=True)
    try:
        assert not any(isinstance(handle, BaseException) for handle in handles), handles
        assert handles[0].provider_ref == handles[1].provider_ref
        await asyncio.gather(first.adestroy(handles[0]), second.adestroy(handles[1]))
        assert await first.aget(handles[0].provider_ref) is None
    finally:
        handle = await first.aget(first._name(spec))
        if handle is not None:
            await first.adestroy(handle)


async def test_real_env_file_values_and_failed_start_cleanup():
    provider = DockerSandboxProvider("test-" + uuid4().hex)
    value = " spaced = value # not a comment "
    spec = SandboxSpec("coder", "env", 1, IMAGE, memory_mb=256, env={"EXPLICIT": value})
    handle = await provider.acreate(spec)
    try:
        result = await provider.aexec(handle, ["python", "-c", "import os; print(repr(os.environ['EXPLICIT']))"])
        assert result.stdout.strip() == repr(value)
    finally:
        await provider.adestroy(handle)
    broken = SandboxSpec("coder", "broken", 1, IMAGE, memory_mb=256, network="agno-missing-" + uuid4().hex)
    with pytest.raises(SandboxError, match="start failed"):
        await provider.acreate(broken)
    assert await provider.aget(provider._name(broken)) is None
