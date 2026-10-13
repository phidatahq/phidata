import asyncio
import json
import os
import subprocess
import sys
from dataclasses import replace

import pytest

from agno.sandbox._exec import _execute
from agno.sandbox.base import ExecResult, SandboxError, SandboxHandle
from agno.sandbox.docker import DockerSandbox


@pytest.mark.parametrize(
    "kwargs",
    [{"cpus": 0}, {"cpus": float("nan")}, {"cpus": True}, {"cpus": "2"}, {"memory_mb": 0}, {"network": "host"}],
)
def test_invalid_limits_and_host_network_are_rejected(kwargs):
    with pytest.raises(ValueError):
        DockerSandbox("python:test", **kwargs)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "kwargs",
    [
        {"session_id": ""},
        {"session_id": "s", "agent_id": ""},
        {"session_id": "s", "generation": 0},
        {"session_id": "s", "generation": True},
        {"session_id": "s", "env": {"A=B": "x"}},
    ],
)
async def test_invalid_create_arguments_are_rejected_before_docker(kwargs):
    sandbox = FakeDocker()
    with pytest.raises(ValueError):
        await sandbox.acreate(**kwargs)
    assert sandbox.calls == []


def test_equal_configuration_has_equal_digest():
    assert DockerSandbox("python:test", cpus=1)._digest("s", None, 1, {}) == DockerSandbox(
        "python:test", cpus=1.0
    )._digest("s", None, 1, {})


def test_sandbox_import_does_not_load_agent_runtime():
    code = "import sys, agno.sandbox.docker; print(any(m.startswith('agno.agents') for m in sys.modules))"
    assert subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True).stdout == "False\n"


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


class FakeDocker(DockerSandbox):
    def __init__(self, **kwargs):
        super().__init__("python:test", namespace="test", **kwargs)
        self.record = None
        self.calls = []
        self.lose_create_response = False
        self.env_file = None

    async def _docker(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        operation = args[1]
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
            with open(args[args.index("--env-file") + 1]) as file:
                self.env_file = file.read()
            self.record = {
                "Id": "container-id",
                "Name": "/" + args[args.index("--name") + 1],
                "Config": {"Labels": labels, "Env": [line for line in self.env_file.splitlines() if line]},
                "State": {"Status": "created"},
            }
            if self.lose_create_response:
                raise asyncio.TimeoutError
            return 0, b"container-id", b""
        if operation == "start":
            self.record["State"]["Status"] = "running"
        elif operation == "pause":
            self.record["State"]["Status"] = "paused"
        elif operation == "unpause":
            self.record["State"]["Status"] = "running"
        elif operation == "stop":
            self.record["State"]["Status"] = "exited"
        elif operation == "rm":
            self.record = None
        return 0, b"", b""


@pytest.mark.asyncio
async def test_create_is_idempotent_and_hardened(monkeypatch):
    monkeypatch.setenv("AGNO_DB_URL", "must-not-be-forwarded")
    sandbox = FakeDocker()
    first = await sandbox.acreate("s", agent_id="coder", env={"MODEL_TOKEN": "explicit"})
    second = await sandbox.acreate("s", agent_id="coder", env={"MODEL_TOKEN": "explicit"})
    assert first == second
    creates = [call for call in sandbox.calls if call[0][1] == "create"]
    assert len(creates) == 1
    argv = creates[0][0]
    assert "--read-only" in argv and "--cap-drop" in argv and "1000:1000" in argv
    assert "AGNO_DB_URL" not in " ".join(argv) and "explicit" not in " ".join(argv)
    assert sandbox.env_file == "HOME=/runtime\nMODEL_TOKEN=explicit\n"
    assert not os.path.exists(argv[argv.index("--env-file") + 1])
    assert not any("docker.sock" in arg for arg in argv)


@pytest.mark.asyncio
async def test_lost_create_response_reconciles_the_same_generation():
    sandbox = FakeDocker()
    sandbox.lose_create_response = True
    handle = await sandbox.acreate("s", agent_id="coder")
    assert handle.state == "running"
    assert len([call for call in sandbox.calls if call[0][1] == "create"]) == 1


@pytest.mark.asyncio
async def test_existing_generation_cannot_change_configuration():
    sandbox = FakeDocker()
    await sandbox.acreate("s", agent_id="coder", env={"A": "1"})
    with pytest.raises(SandboxError, match="different configuration"):
        await sandbox.acreate("s", agent_id="coder", env={"A": "2"})


@pytest.mark.asyncio
async def test_stop_destroy_and_identity_checks():
    sandbox = FakeDocker()
    handle = await sandbox.acreate("s", agent_id="coder")
    with pytest.raises(SandboxError, match="identity changed"):
        await sandbox.adestroy(replace(handle, generation=2))
    assert sandbox.record is not None
    await sandbox.astop(handle)
    with pytest.raises(SandboxError, match="new generation"):
        await sandbox.acreate("s", agent_id="coder")
    await sandbox.adestroy(handle)
    await sandbox.adestroy(handle)
    assert await sandbox.aget(handle.provider_ref) is None


@pytest.mark.asyncio
async def test_foreign_namespace_is_never_removed():
    sandbox = FakeDocker()
    handle = await sandbox.acreate("s", agent_id="coder")
    sandbox.record["Config"]["Labels"]["io.agno.sandbox.namespace"] = "other"
    with pytest.raises(SandboxError, match="namespace"):
        await sandbox.adestroy(handle)
    assert not any(call[0][1] == "rm" for call in sandbox.calls)


def test_sync_wrappers():
    sandbox = FakeDocker()
    handle = sandbox.create("s", agent_id="coder")
    assert sandbox.get(handle.provider_ref) == handle
    sandbox.stop(handle)
    sandbox.destroy(handle)


@pytest.mark.asyncio
async def test_sync_wrappers_inside_running_loop():
    sandbox = FakeDocker()
    handle = sandbox.create("s", agent_id="coder")
    assert handle.state == "running"
    sandbox.destroy(handle)


@pytest.mark.asyncio
async def test_exec_validates_before_contacting_docker():
    sandbox = FakeDocker()
    handle = SandboxHandle("id", "name", "a", "s", 1, "running", "digest")
    for args in ["echo bad", [], ["a\x00b"]]:
        with pytest.raises(ValueError):
            await sandbox.aexec(handle, args)
    assert sandbox.calls == []


@pytest.mark.asyncio
async def test_transport_failure_stops_remote_execution():
    class FailedExec(FakeDocker):
        async def _docker(self, *args, **kwargs):
            if args[1] == "exec":
                raise SandboxError("lost command transport")
            return await super()._docker(*args, **kwargs)

    sandbox = FailedExec()
    handle = await sandbox.acreate("s", agent_id="coder")
    with pytest.raises(SandboxError, match="lost command"):
        await sandbox.aexec(handle, ["example"])
    assert (await sandbox.aget(handle.provider_ref)).state == "exited"


@pytest.mark.asyncio
async def test_invalid_command_result_stops_remote_execution():
    class InvalidExec(FakeDocker):
        async def _docker(self, *args, **kwargs):
            if args[1] == "exec":
                return 0, b"invalid json", b""
            return await super()._docker(*args, **kwargs)

    sandbox = InvalidExec()
    handle = await sandbox.acreate("s", agent_id="coder")
    with pytest.raises(SandboxError, match="invalid command"):
        await sandbox.aexec(handle, ["example"])
    assert (await sandbox.aget(handle.provider_ref)).state == "exited"


@pytest.mark.asyncio
@pytest.mark.parametrize("env", [{"A": "multi\nline"}, {"A": "cr\r"}, {"#A": "x"}, {"A B": "x"}])
async def test_env_that_cannot_be_written_to_an_env_file_is_rejected(env):
    sandbox = FakeDocker()
    with pytest.raises(ValueError, match="env"):
        await sandbox.acreate("s", env=env)
    assert not any(call[0][1] == "create" for call in sandbox.calls)


@pytest.mark.asyncio
async def test_failed_start_removes_the_never_started_container():
    class FailedStart(FakeDocker):
        async def _docker(self, *args, **kwargs):
            if args[1] == "start":
                self.calls.append((args, kwargs))
                return 1, b"", b"network Host not found"
            return await super()._docker(*args, **kwargs)

    sandbox = FailedStart()
    with pytest.raises(SandboxError, match="start failed"):
        await sandbox.acreate("s", agent_id="coder")
    assert sandbox.record is None


@pytest.mark.asyncio
async def test_agent_id_is_optional():
    sandbox = FakeDocker()
    handle = await sandbox.acreate("s")
    assert handle.agent_id is None and handle.generation == 1
    assert await sandbox.acreate("s") == handle


# ---------------------------------------------------------------------------
# Warm path: pause and resume keep the generation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pause_keeps_the_generation_and_only_resume_revives_it():
    sandbox = FakeDocker()
    handle = await sandbox.acreate("session", agent_id="coder")
    await sandbox.apause(handle)
    assert (await sandbox.aget(handle.provider_ref)).state == "paused"
    await sandbox.apause(handle)  # idempotent
    with pytest.raises(SandboxError, match="paused; resume"):
        await sandbox.aexec(handle, ["true"])
    # Create cannot tell a warm pause from a restore that died halfway, so it refuses to guess.
    with pytest.raises(SandboxError, match="paused; resume it or destroy it"):
        await sandbox.acreate("session", agent_id="coder")
    assert (await sandbox.aget(handle.provider_ref)).state == "paused"
    # The owner, who paused it, resumes it explicitly.
    resumed = await sandbox.aresume(handle)
    assert resumed.provider_ref == handle.provider_ref and resumed.state == "running"
    assert [call[0][1] for call in sandbox.calls if call[0][1] in ("pause", "unpause", "create")] == [
        "create",
        "pause",
        "unpause",
    ]


@pytest.mark.asyncio
async def test_resume_is_explicit_and_only_from_paused():
    sandbox = FakeDocker()
    handle = await sandbox.acreate("session")
    assert (await sandbox.aresume(handle)).state == "running"  # already running: no-op
    await sandbox.apause(handle)
    assert (await sandbox.aresume(handle)).state == "running"
    await sandbox.astop(handle)
    with pytest.raises(SandboxError, match="not paused; recovery requires a new generation"):
        await sandbox.aresume(handle)
    with pytest.raises(SandboxError, match="Only a running sandbox"):
        await sandbox.apause(handle)


@pytest.mark.asyncio
async def test_stop_and_destroy_still_take_the_cold_path_from_paused():
    sandbox = FakeDocker()
    handle = await sandbox.acreate("session")
    await sandbox.apause(handle)
    await sandbox.astop(handle)
    assert (await sandbox.aget(handle.provider_ref)).state == "exited"
    with pytest.raises(SandboxError, match="not running; recovery requires a new generation"):
        await sandbox.acreate("session")
    await sandbox.adestroy(handle)
    assert await sandbox.aget(handle.provider_ref) is None


@pytest.mark.asyncio
async def test_providers_without_a_native_pause_say_so():
    from agno.sandbox.base import Sandbox

    class ColdOnly(Sandbox):
        async def acreate(self, session_id, *, agent_id=None, generation=1, env=None):
            raise NotImplementedError

        async def aget(self, provider_ref):
            return None

        async def aexec(self, handle, argv, *, timeout=60, max_output_bytes=1_048_576, stdin=b""):
            raise NotImplementedError

        async def astop(self, handle):
            pass

        async def adestroy(self, handle):
            pass

    handle = SandboxHandle("ref", "name", None, "s", 1, "running", "digest")
    with pytest.raises(NotImplementedError, match="pausing"):
        await ColdOnly().apause(handle)
    with pytest.raises(NotImplementedError, match="resuming"):
        await ColdOnly().aresume(handle)


# ---------------------------------------------------------------------------
# Runtime server transport: published loopback port, pooled HTTP, exec fallback
# ---------------------------------------------------------------------------


class ServedDocker(FakeDocker):
    """A fake daemon that publishes the runtime port and a fake runtime server behind it."""

    def __init__(self, **kwargs):
        super().__init__(network="bridge", runtime_port=8765, **kwargs)
        self.http_requests = []
        self.http_status = 200
        self.http_body = {"version": 1, "execution_id": "e", "accepted": True}
        self.http_error = None

    async def _docker(self, *args, **kwargs):
        code, out, err = await super()._docker(*args, **kwargs)
        if args[1] == "create":
            self.record["NetworkSettings"] = {"Ports": {"8765/tcp": [{"HostIp": "127.0.0.1", "HostPort": "49152"}]}}
        return code, out, err

    def _http_client(self):
        import httpx

        async def handler(request):
            self.http_requests.append((request.method, request.url.path, request.content))
            if self.http_error is not None:
                raise self.http_error
            token = next(
                line.split("=", 1)[1]
                for line in self.env_file.splitlines()
                if line.startswith("AGNO_SANDBOX_RUNTIME_TOKEN=")
            )
            if request.headers.get("Authorization") != "Bearer " + token:
                return httpx.Response(401, json={"error": "wrong token"})
            if request.url.path == "/health":
                return httpx.Response(200, json={"version": 1, "ok": True})
            return httpx.Response(self.http_status, json=self.http_body)

        return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def _create_args(provider):
    return next(call[0] for call in provider.calls if call[0][1] == "create")


@pytest.mark.asyncio
async def test_runtime_port_publishes_on_loopback_and_serves_the_runtime():
    provider = ServedDocker()
    handle = await provider.acreate("session", agent_id="coder")
    args = _create_args(provider)
    assert args[args.index("--publish") + 1] == "127.0.0.1::8765"
    assert list(args[args.index("--entrypoint") :])[:7] == [
        "--entrypoint",
        "python",
        "python:test",
        "-I",
        "-m",
        "agno.sandbox.runtime",
        "supervise",
    ]
    assert "--label" in args and "io.agno.sandbox.runtime=8765" in args
    assert handle.runtime_url == "http://127.0.0.1:49152"
    # Creation waited for the server to answer before handing the sandbox out, with the token.
    assert [path for _, path, _ in provider.http_requests] == ["/health"]
    # A fresh token per container, delivered through the private env file, read back from the
    # container's environment onto the handle, and never shown in the handle's repr.
    token = next(line.split("=", 1)[1] for line in provider.env_file.splitlines() if line.startswith("AGNO_SANDBOX"))
    assert len(token) >= 32 and handle.runtime_token == token
    assert token not in repr(handle)
    assert (await provider.aget(handle.provider_ref)).runtime_token == token


@pytest.mark.asyncio
async def test_rpc_goes_over_http_and_never_touches_compute_on_failure():
    provider = ServedDocker()
    handle = await provider.acreate("session")
    result = await provider.arpc(handle, "start", b'{"execution_id": "e"}')
    assert result.exit_code == 0 and json.loads(result.stdout)["accepted"] is True
    assert provider.http_requests[-1] == ("POST", "/start", b'{"execution_id": "e"}')
    provider.http_status, provider.http_body = 409, {"error": "already exists with different input"}
    failed = await provider.arpc(handle, "start", b'{"execution_id": "e"}')
    assert failed.exit_code == 1 and "different input" in failed.stderr
    import httpx

    provider.http_error = httpx.ConnectError("gone")
    with pytest.raises(SandboxError, match="runtime request failed"):
        await provider.arpc(handle, "poll", b'{"execution_id": "e", "cursor": 0}')
    assert (await provider.aget(handle.provider_ref)).state == "running"
    assert not any(call[0][1] in ("stop", "exec") for call in provider.calls)
    with pytest.raises(ValueError, match="start/poll"):
        await provider.arpc(handle, "shell", b"{}")


@pytest.mark.asyncio
async def test_rpc_over_http_makes_no_daemon_calls_and_falls_back_to_exec_without_a_port():
    served = ServedDocker()
    handle = await served.acreate("session")
    before = len(served.calls)
    for _ in range(3):
        await served.arpc(handle, "poll", b'{"execution_id": "e", "cursor": 0}')
    assert len(served.calls) == before, "the daemon is not on the per-request path"
    plain = FakeDocker()
    handle = await plain.acreate("session")
    assert handle.runtime_url is None
    seen = []

    async def aexec(handle, argv, **kwargs):
        seen.append((argv, kwargs))
        return ExecResult(0, "{}", "")

    plain.aexec = aexec  # type: ignore[method-assign]
    await plain.arpc(handle, "poll", b'{"execution_id": "e", "cursor": 0, "wait": 5}')
    argv, kwargs = seen[0]
    assert argv == ["python", "-I", "-m", "agno.sandbox.runtime", "poll"]
    assert kwargs["stdin"] == b'{"execution_id": "e", "cursor": 0, "wait": 5}' and kwargs["timeout"] == 20


def test_runtime_port_requires_a_network_and_is_part_of_the_configuration():
    with pytest.raises(ValueError, match="needs a network"):
        DockerSandbox("python:test", runtime_port=8765)
    with pytest.raises(ValueError, match="between 1 and 65535"):
        DockerSandbox("python:test", network="bridge", runtime_port=0)
    for host in ("", "-x", "10.0.0.5:80", "a b", "http://h"):
        with pytest.raises(ValueError, match="bare IP address or host name"):
            DockerSandbox("python:test", network="bridge", runtime_port=8765, runtime_host=host)
    served = DockerSandbox("python:test", network="bridge", runtime_port=8765)
    plain = DockerSandbox("python:test", network="bridge")
    remote = DockerSandbox("python:test", network="bridge", runtime_port=8765, runtime_host="10.0.0.5")
    digests = {p._digest("s", None, 1, {}) for p in (served, plain, remote)}
    assert len(digests) == 3, "port and host are part of the generation's configuration"


@pytest.mark.asyncio
async def test_runtime_host_publishes_and_advertises_the_daemon_hosts_address():
    """Replicas on other machines reach a shared daemon's containers through its address."""

    class Remote(ServedDocker):
        def __init__(self):
            FakeDocker.__init__(self, network="bridge", runtime_port=8765, runtime_host="10.0.0.5")
            self.http_requests, self.http_status, self.http_error = [], 200, None
            self.http_body = {"version": 1, "execution_id": "e", "accepted": True}

    provider = Remote()
    handle = await provider.acreate("session")
    args = _create_args(provider)
    assert args[args.index("--publish") + 1] == "10.0.0.5::8765"
    assert handle.runtime_url == "http://10.0.0.5:49152"


@pytest.mark.asyncio
async def test_requests_carry_the_token_and_a_user_cannot_supply_one():
    provider = ServedDocker()
    handle = await provider.acreate("session")
    await provider.arpc(handle, "poll", b'{"execution_id": "e", "cursor": 0}')
    # The fake server returned 200 only because the bearer header matched its token.
    assert provider.http_requests[-1][1] == "/poll"
    stale = SandboxHandle(**{**handle.__dict__, "runtime_token": "wrong"})
    refused = await provider.arpc(stale, "poll", b'{"execution_id": "e", "cursor": 0}')
    assert refused.exit_code == 1 and "wrong token" in refused.stderr
    with pytest.raises(ValueError, match="generated per container"):
        await ServedDocker().acreate("other", env={"AGNO_SANDBOX_RUNTIME_TOKEN": "mine"})


@pytest.mark.asyncio
async def test_create_fails_when_the_runtime_server_never_answers(monkeypatch):
    import httpx

    from agno.sandbox import docker as docker_module

    monkeypatch.setattr(docker_module, "_RUNTIME_READY_SECONDS", 0.3)
    provider = ServedDocker()
    provider.http_error = httpx.ConnectError("not up")
    with pytest.raises(SandboxError, match="did not become ready"):
        await provider.acreate("session")


@pytest.mark.asyncio
async def test_list_enumerates_the_namespace_from_daemon_labels():
    provider = ServedDocker()
    handle = await provider.acreate("session", agent_id="coder")
    original = provider._docker

    async def docker(*args, **kwargs):
        if args[:2] == ("container", "ls"):
            assert f"label=io.agno.sandbox.namespace={provider.namespace}" in args
            return 0, (handle.provider_ref + "\n").encode(), b""
        return await original(*args, **kwargs)

    provider._docker = docker  # type: ignore[method-assign]
    [listed] = await provider.alist()
    assert (listed.provider_ref, listed.session_id, listed.runtime_url, listed.runtime_token) == (
        handle.provider_ref,
        "session",
        handle.runtime_url,
        handle.runtime_token,
    )
