import asyncio
import json
import sys
from dataclasses import replace

import pytest

from agno.sandbox._exec import _execute
from agno.sandbox.base import SandboxError, SandboxHandle, SandboxSpec
from agno.sandbox.docker import DockerSandboxProvider


def spec(**kwargs):
    return SandboxSpec(agent_id="coder", session_id="s", generation=1, image="python:test", **kwargs)


@pytest.mark.parametrize("kwargs", [{"cpus": 0}, {"cpus": float("nan")}, {"memory_mb": 0}, {"network": "host"}])
def test_invalid_limits_and_host_network_are_rejected(kwargs):
    with pytest.raises(ValueError):
        spec(**kwargs)


def test_environment_is_copied_and_not_in_repr():
    env = {"TOKEN": "secret"}
    value = spec(env=env)
    env["TOKEN"] = "changed"
    assert value.env["TOKEN"] == "secret"
    assert "secret" not in repr(value)
    with pytest.raises(TypeError):
        value.env["TOKEN"] = "mutated"


def test_command_runner_retains_exit_status_and_bounds_output():
    result = _execute(
        {
            "argv": [sys.executable, "-c", "print('x' * 10000); raise SystemExit(3)"],
            "timeout": 5,
            "max_output_bytes": 100,
        }
    )
    assert result["output_limited"] and len(result["stdout"].encode()) <= 100
    assert result["exit_code"] != 0


def test_command_runner_timeout():
    result = _execute(
        {"argv": [sys.executable, "-c", "import time; time.sleep(30)"], "timeout": 0.05, "max_output_bytes": 100}
    )
    assert result["timed_out"] and result["exit_code"] != 0


def test_command_runner_missing_executable():
    result = _execute({"argv": ["/does/not/exist"], "timeout": 1, "max_output_bytes": 100})
    assert result["exit_code"] == 127


class FakeDocker(DockerSandboxProvider):
    def __init__(self):
        super().__init__("test")
        self.record = None
        self.volumes = {}
        self.calls = []
        self.lose_create_response = False

    async def _docker(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        operation = args[1]
        if args[0] == "volume":
            name = args[-1]
            if operation == "inspect":
                return (
                    (0, json.dumps([self.volumes[name]]).encode(), b"")
                    if name in self.volumes
                    else (1, b"", b"no such volume")
                )
            if operation == "create":
                fields = {}
                for flag, field in (("--opt", "Options"), ("--label", "Labels")):
                    fields[field] = dict(args[i + 1].split("=", 1) for i, arg in enumerate(args) if arg == flag)
                self.volumes[name] = {"Name": name, "Driver": "local", **fields}
            elif operation == "rm":
                self.volumes.pop(name, None)
            return 0, b"", b""
        if operation == "inspect":
            if self.record is None:
                return 1, b"", b"No such container"
            return 0, json.dumps([self.record]).encode(), b""
        if operation == "create":
            labels = {}
            for i, arg in enumerate(args):
                if arg == "--label":
                    key, value = args[i + 1].split("=", 1)
                    labels[key] = value
            self.record = {
                "Id": "container-id",
                "Name": "/" + args[args.index("--name") + 1],
                "Config": {"Labels": labels},
                "State": {"Status": "created"},
            }
            if self.lose_create_response:
                raise asyncio.TimeoutError
            return 0, b"container-id", b""
        if operation == "start":
            self.record["State"]["Status"] = "running"
        elif operation == "stop":
            self.record["State"]["Status"] = "exited"
        elif operation == "rm":
            self.record = None
        return 0, b"", b""


@pytest.mark.asyncio
async def test_create_is_idempotent_and_hardened(monkeypatch):
    monkeypatch.setenv("AGNO_DB_URL", "must-not-be-forwarded")
    provider = FakeDocker()
    first = await provider.acreate(spec(env={"MODEL_TOKEN": "explicit"}))
    second = await provider.acreate(spec(env={"MODEL_TOKEN": "explicit"}))
    assert first == second
    creates = [call for call in provider.calls if call[0][:2] == ("container", "create")]
    assert len(creates) == 1
    argv = creates[0][0]
    assert "--read-only" in argv and "--cap-drop" in argv and "1000:1000" in argv
    assert "AGNO_DB_URL" not in " ".join(argv) and "MODEL_TOKEN=explicit" in argv
    assert not any("docker.sock" in arg for arg in argv)


@pytest.mark.asyncio
async def test_lost_create_response_reconciles_the_same_generation():
    provider = FakeDocker()
    provider.lose_create_response = True
    handle = await provider.acreate(spec())
    assert handle.state == "running"
    assert len([call for call in provider.calls if call[0][:2] == ("container", "create")]) == 1


@pytest.mark.asyncio
async def test_existing_generation_cannot_change_configuration():
    provider = FakeDocker()
    await provider.acreate(spec())
    with pytest.raises(SandboxError, match="different configuration"):
        await provider.acreate(spec(cpus=1))


@pytest.mark.asyncio
async def test_stop_destroy_and_identity_checks():
    provider = FakeDocker()
    handle = await provider.acreate(spec())
    with pytest.raises(SandboxError, match="identity changed"):
        await provider.adestroy(replace(handle, generation=2))
    assert provider.record is not None
    await provider.astop(handle)
    with pytest.raises(SandboxError, match="new generation"):
        await provider.acreate(spec())
    await provider.adestroy(handle)
    await provider.adestroy(handle)
    assert await provider.aget(handle.provider_ref) is None


@pytest.mark.asyncio
async def test_foreign_namespace_is_never_removed():
    provider = FakeDocker()
    handle = await provider.acreate(spec())
    provider.record["Config"]["Labels"]["io.agno.sandbox.namespace"] = "other"
    with pytest.raises(SandboxError, match="namespace"):
        await provider.adestroy(handle)
    assert not any(call[0][1] == "rm" for call in provider.calls)


def test_sync_provider_wrappers():
    provider = FakeDocker()
    handle = provider.create(spec())
    assert provider.get(handle.provider_ref) == handle
    provider.stop(handle)
    provider.destroy(handle)


@pytest.mark.asyncio
async def test_exec_validates_before_contacting_docker():
    provider = FakeDocker()
    handle = SandboxHandle("id", "name", "a", "s", 1, "running", "digest")
    for args in ["echo bad", [], ["a\x00b"]]:
        with pytest.raises(ValueError):
            await provider.aexec(handle, args)
    assert provider.calls == []


@pytest.mark.asyncio
async def test_transport_failure_stops_remote_execution():
    class FailedExec(FakeDocker):
        async def _docker(self, *args, **kwargs):
            if args[1] == "exec":
                raise SandboxError("lost command transport")
            return await super()._docker(*args, **kwargs)

    provider = FailedExec()
    handle = await provider.acreate(spec())
    with pytest.raises(SandboxError, match="lost command"):
        await provider.aexec(handle, ["example"])
    assert (await provider.aget(handle.provider_ref)).state == "exited"


@pytest.mark.asyncio
async def test_invalid_command_result_stops_remote_execution():
    class InvalidExec(FakeDocker):
        async def _docker(self, *args, **kwargs):
            if args[1] == "exec":
                return 0, b"invalid json", b""
            return await super()._docker(*args, **kwargs)

    provider = InvalidExec()
    handle = await provider.acreate(spec())
    with pytest.raises(SandboxError, match="invalid command"):
        await provider.aexec(handle, ["example"])
    assert (await provider.aget(handle.provider_ref)).state == "exited"


@pytest.mark.asyncio
async def test_owned_volumes_are_bounded_and_removed_after_lost_container_delete():
    provider = FakeDocker()
    handle = await provider.acreate(spec(workspace_mb=32))
    assert len(provider.volumes) == 2
    volume = provider.volumes[handle.name + "-workspace"]
    assert volume["Options"]["type"] == "tmpfs"
    assert "size=32m" in volume["Options"]["o"]
    provider.record = None  # Container removal succeeded, but its response was lost.
    await provider.adestroy(handle)
    assert provider.volumes == {}


@pytest.mark.asyncio
async def test_foreign_orphan_volume_is_not_removed():
    provider = FakeDocker()
    handle = await provider.acreate(spec())
    provider.record = None
    provider.volumes[handle.name + "-workspace"]["Labels"]["io.agno.sandbox.namespace"] = "other"
    with pytest.raises(SandboxError, match="different sandbox identity"):
        await provider.adestroy(handle)
    assert len(provider.volumes) == 2


@pytest.mark.asyncio
async def test_failed_container_create_removes_its_volumes_so_a_corrected_spec_can_retry():
    class FailedCreate(FakeDocker):
        async def _docker(self, *args, **kwargs):
            if args[:2] == ("container", "create") and "python:missing" in args:
                self.calls.append((args, kwargs))
                return 1, b"", b"No such image"
            return await super()._docker(*args, **kwargs)

    provider = FailedCreate()
    with pytest.raises(SandboxError, match="No such image"):
        await provider.acreate(SandboxSpec(agent_id="coder", session_id="s", generation=1, image="python:missing"))
    assert provider.volumes == {}
    assert (await provider.acreate(spec())).state == "running"


@pytest.mark.asyncio
async def test_reacquire_rejects_a_generation_left_paused_by_an_interrupted_transfer():
    provider = FakeDocker()
    handle = await provider.acreate(spec())
    provider.record["State"]["Status"] = "paused"
    with pytest.raises(SandboxError, match="not running"):
        await provider.aexec(handle, ["example"])
    with pytest.raises(SandboxError, match="interrupted checkpoint transfer"):
        await provider.acreate(spec())
    assert not any(call[0][:2] == ("container", "unpause") for call in provider.calls)
