"""Amazon Bedrock AgentCore Runtime sandboxes: one runtime session per sandbox generation."""

import asyncio
import base64
import hashlib
import json
import math
import random
import shlex
import tempfile
import time
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence, Set
from uuid import uuid4

from agno.sandbox.base import ExecResult, Sandbox, SandboxError, SandboxHandle, _identity
from agno.sandbox.checkpoint import CheckpointArchive, CheckpointRef, CheckpointStore
from agno.sandbox.transfer import DEFAULT_NATIVE_EXCLUSIONS, _ArchiveTransfer

_GUARD_EXIT = 125
# AgentCore rejects these before anything runs, so a retry cannot repeat work.
# Throttling appears when many sessions start at once: the default quota is 25
# new sessions per second.
_RETRYABLE = ("RetryableConflictException", "ThrottlingException", "ThrottledException")
# Gateway and server errors leave the outcome unknown. Every invocation and stop
# is idempotent (claim and start by identity, describe and poll read only), so
# those retry them; a command could run twice, so it never does.
_SERVER_ERRORS = ("500", "502", "503", "504", "InternalServerException", "ServiceException")
_ATTEMPTS = 10
_MAX_COMMAND = 64 * 1024
# Checkpoint bytes per invocation. Base64 makes the payload a third larger, well
# under AgentCore's 100 MB request and response limit.
_CHUNK = 8 * 1024 * 1024
_RUNNER = Path(__file__).with_name("_exec.py").read_text()


def _error_code(error: BaseException) -> str:
    response = getattr(error, "response", None)
    return response.get("Error", {}).get("Code", "") if isinstance(response, dict) else ""


async def _thread(function: Any, *args: Any, **kwargs: Any) -> Any:
    # A boto3 call cannot be cancelled once sent. Drain it so a cancelled caller
    # never races a retry or cleanup against a request still in flight.
    task = asyncio.ensure_future(asyncio.to_thread(function, *args, **kwargs))
    try:
        return await asyncio.shield(task)
    except asyncio.CancelledError:
        await task
        raise


class AgentCoreSandbox(Sandbox):
    """Sandbox compute on a deployed AgentCore Runtime.

    The runtime's image must run ``python -I -m agno.sandbox.agentcore_server serve``
    as its entrypoint. Each generation is the runtime session named after its
    identity, so create is idempotent and a lost create reply is found again by
    name. Every session is a microVM with 2 vCPU and 8 GiB, internet egress in
    PUBLIC mode, and the runtime's IAM role. Code in the sandbox can use that
    role, so give it only the model access the harness needs.

    Stop and destroy end the microVM. AgentCore starts a fresh microVM if a stopped
    session is called again; this class treats such an unclaimed microVM as gone
    and stops it, so recovery takes a new generation, as on Docker. Pause is not
    supported. Files live on the microVM's disk; AgentCore session storage is not
    used because SQLite cannot open a database on it.
    """

    def __init__(
        self,
        runtime_arn: str,
        *,
        namespace: str = "default",
        qualifier: str = "DEFAULT",
        lifetime: int = 3600,
        boto_session: Optional[Any] = None,
        request_timeout: float = 120,
        max_connections: int = 10,
    ) -> None:
        try:
            import boto3
            from botocore.config import Config
        except ImportError as error:
            raise ImportError("Install agno[agentcore-sandbox] to use AgentCore sandboxes") from error
        parts = runtime_arn.split(":")
        if len(parts) != 6 or parts[2] != "bedrock-agentcore" or not parts[5].startswith("runtime/"):
            raise ValueError("AgentCore runtime ARN must look like arn:aws:bedrock-agentcore:REGION:ACCOUNT:runtime/ID")
        if not namespace or "\x00" in namespace or type(lifetime) is not int or lifetime < 60:
            raise ValueError("AgentCore namespace must be nonempty and lifetime at least 60 seconds")
        if request_timeout < 60:
            raise ValueError("AgentCore request timeout must cover a 30 second long poll")
        if type(max_connections) is not int or max_connections < 1:
            raise ValueError("AgentCore max_connections must be a positive integer")
        self.runtime_arn, self.namespace, self.qualifier, self.lifetime = runtime_arn, namespace, qualifier, lifetime
        session = boto_session or boto3.session.Session()
        # An uncertain command must never be sent twice, so the SDK does not retry.
        # Rejections that AgentCore returns before running anything are retried
        # explicitly in _call.
        config = Config(
            region_name=parts[3],
            read_timeout=request_timeout,
            connect_timeout=10,
            retries={"total_max_attempts": 1, "mode": "standard"},
            # Each session in flight holds a connection, and a long poll holds it
            # for up to 30 seconds. Size this to the concurrent sessions served.
            max_pool_connections=max_connections,
        )
        self._data = session.client("bedrock-agentcore", config=config)
        # Sessions this object stopped. Calling one again would only start an
        # unclaimed replacement microVM.
        self._stopped: Set[str] = set()

    def _name(self, session_id: str, agent_id: Optional[str], generation: int) -> str:
        identity = json.dumps([self.namespace, agent_id, session_id, generation])
        return "agno-" + hashlib.sha256(identity.encode()).hexdigest()[:40]

    def _digest(self, session_id: str, agent_id: Optional[str], generation: int, env: Mapping[str, str]) -> str:
        data = {
            "runtime_arn": self.runtime_arn,
            "qualifier": self.qualifier,
            "lifetime": self.lifetime,
            "agent_id": agent_id,
            "session_id": session_id,
            "generation": generation,
            "env": dict(env),
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()

    @staticmethod
    def _call(function: Any, *, idempotent: bool = False, **kwargs: Any) -> Any:
        retryable = _RETRYABLE + _SERVER_ERRORS if idempotent else _RETRYABLE
        for attempt in range(_ATTEMPTS):
            try:
                return function(**kwargs)
            except Exception as error:
                if _error_code(error) not in retryable or attempt == _ATTEMPTS - 1:
                    raise
                # Full jitter spreads a burst of throttled creates across the window.
                time.sleep(random.uniform(0, min(8.0, 0.5 * 2**attempt)))

    def _invoke(self, provider_ref: str, operation: str, /, **payload: Any) -> Any:
        body = json.dumps(dict(payload, op=operation)).encode()
        response = self._call(
            self._data.invoke_agent_runtime,
            idempotent=True,
            agentRuntimeArn=self.runtime_arn,
            qualifier=self.qualifier,
            runtimeSessionId=provider_ref,
            payload=body,
            contentType="application/json",
            accept="application/json",
        )
        reply = json.loads(response["response"].read())
        if not isinstance(reply, dict) or not reply.get("ok"):
            reason = reply.get("error", reply) if isinstance(reply, dict) else reply
            raise SandboxError("AgentCore sandbox refused " + operation + ": " + str(reason)[:1000])
        return reply["value"]

    def _handle(self, provider_ref: str, metadata: Mapping[str, str]) -> SandboxHandle:
        if metadata.get("namespace") != self.namespace:
            raise SandboxError("AgentCore computer does not belong to this sandbox namespace")
        try:
            return SandboxHandle(
                provider_ref=provider_ref,
                name=provider_ref,
                agent_id=metadata["agent"] or None,
                session_id=metadata["session"],
                generation=int(metadata["generation"]),
                state="running",
                config_digest=metadata["config"],
            )
        except (KeyError, TypeError, ValueError) as error:
            raise SandboxError("AgentCore computer has incomplete sandbox identity") from error

    async def aget(self, provider_ref: str) -> Optional[SandboxHandle]:
        if not provider_ref.startswith("agno-") or len(provider_ref) < 33:
            raise ValueError("Invalid AgentCore sandbox reference")
        if provider_ref in self._stopped:
            return None
        description = await _thread(self._invoke, provider_ref, "describe")
        if not description["claimed"]:
            # This call started a replacement microVM because the claimed one has
            # ended. Release it and report the generation gone.
            await self._stop(provider_ref)
            return None
        return self._handle(provider_ref, description["metadata"])

    async def _owned(self, handle: SandboxHandle) -> SandboxHandle:
        current = await self.aget(handle.provider_ref)
        if current is None:
            raise SandboxError("Sandbox is not running")
        if (current.agent_id, current.session_id, current.generation, current.config_digest) != (
            handle.agent_id,
            handle.session_id,
            handle.generation,
            handle.config_digest,
        ):
            raise SandboxError("Sandbox identity changed; refusing the operation")
        return current

    async def acreate(
        self,
        session_id: str,
        *,
        agent_id: Optional[str] = None,
        generation: int = 1,
        env: Optional[Mapping[str, str]] = None,
    ) -> SandboxHandle:
        values = _identity(session_id, agent_id, generation, env)
        name = self._name(session_id, agent_id, generation)
        if name in self._stopped:
            raise SandboxError("Sandbox generation is not running; recovery requires a new generation")
        digest = self._digest(session_id, agent_id, generation, values)
        metadata = {
            "namespace": self.namespace,
            "agent": agent_id or "",
            "session": session_id,
            "generation": str(generation),
            "config": digest,
        }
        try:
            await _thread(self._invoke, name, "claim", metadata=metadata, env=values, lifetime=self.lifetime)
        except SandboxError as error:
            if "different identity" in str(error):
                raise SandboxError("Sandbox generation already exists with different configuration") from error
            raise
        return self._handle(name, metadata)

    async def arpc(self, handle: SandboxHandle, operation: str, payload: bytes) -> ExecResult:
        """Runtime start/poll through InvokeAgentRuntime to the in-computer runtime server.

        A failed or lost reply never touches compute: the caller reconciles.
        """
        if operation not in ("start", "poll") or not isinstance(payload, bytes) or len(payload) > 1024 * 1024:
            raise ValueError("Runtime RPC requires start/poll and a payload no larger than 1 MiB")
        if handle.provider_ref in self._stopped:
            raise SandboxError("Sandbox is not running")
        reply = await _thread(self._invoke, handle.provider_ref, "rpc", operation=operation, payload=payload.decode())
        body = str(reply["body"])[: 4 * 1024 * 1024]
        if reply["status"] != 200:
            return ExecResult(exit_code=1, stdout="", stderr=body)
        return ExecResult(exit_code=0, stdout=body, stderr="")

    async def aexec(
        self,
        handle: SandboxHandle,
        argv: Sequence[str],
        *,
        timeout: float = 60,
        max_output_bytes: int = 1_048_576,
        stdin: bytes = b"",
    ) -> ExecResult:
        if isinstance(argv, (str, bytes)) or not argv or any(not isinstance(arg, str) or "\x00" in arg for arg in argv):
            raise ValueError("Commands must be a nonempty sequence of strings")
        if not math.isfinite(timeout) or timeout <= 0 or not 1 <= max_output_bytes <= 4 * 1024 * 1024:
            raise ValueError("Timeout must be positive and output limit must be between 1 byte and 4 MiB")
        if timeout > 3500:
            raise ValueError("AgentCore commands run for at most an hour")
        if not isinstance(stdin, bytes) or len(stdin) > 8 * 1024 * 1024:
            raise ValueError("Command stdin must be bytes no larger than 8 MiB")
        await self._owned(handle)
        request = json.dumps(
            {
                "argv": list(argv),
                "timeout": timeout,
                "max_output_bytes": max_output_bytes,
                "stdin": base64.b64encode(stdin).decode("ascii"),
            }
        ).encode()
        # The command API has no stdin, so the runner's request is staged first and
        # handed to the command by the guard, which deletes it.
        name = uuid4().hex
        command = shlex.join(
            ["python", "-I", "-m", "agno.sandbox.agentcore_server", "exec", "--stdin", name, "--"]
            + ["python", "-I", "-c", _RUNNER]
        )
        if len(command.encode()) > _MAX_COMMAND:
            raise SandboxError("AgentCore command exceeds 64 KiB")
        try:
            await _thread(self._invoke, handle.provider_ref, "stage", name=name, data=request.hex())
            code, out, err, timed_out = await _thread(self._command, handle.provider_ref, command, timeout + 15)
        except BaseException:
            # The command may still be running remotely. Stop compute to bound it;
            # recovery belongs to the caller.
            await asyncio.shield(self.astop(handle))
            raise
        if code == _GUARD_EXIT and "not claimed" in err:
            raise SandboxError("AgentCore session answered from an unclaimed replacement computer")
        try:
            if code or timed_out:
                raise ValueError(err[-500:] or "command transport timed out")
            result = ExecResult(**json.loads(out))
        except (TypeError, ValueError) as error:
            await self.astop(handle)
            raise SandboxError("Sandbox command transport failed: " + str(error)[:500]) from error
        if result.timed_out or result.output_limited:
            await self.astop(handle)
        return result

    def _command(self, provider_ref: str, command: str, timeout: float) -> tuple:
        response = self._call(
            self._data.invoke_agent_runtime_command,
            agentRuntimeArn=self.runtime_arn,
            qualifier=self.qualifier,
            runtimeSessionId=provider_ref,
            contentType="application/json",
            accept="application/vnd.amazon.eventstream",
            body={"command": command, "timeout": min(3600, max(1, math.ceil(timeout)))},
        )
        stdout, stderr, stop = [], [], None
        for event in response["stream"]:
            chunk = event.get("chunk", {})
            if "contentDelta" in chunk:
                stdout.append(chunk["contentDelta"].get("stdout") or "")
                stderr.append(chunk["contentDelta"].get("stderr") or "")
            elif "contentStop" in chunk:
                stop = chunk["contentStop"]
        if stop is None:
            raise SandboxError("AgentCore command stream ended without an exit status")
        return int(stop.get("exitCode", -1)), "".join(stdout), "".join(stderr), stop.get("status") == "TIMED_OUT"

    async def _stop(self, provider_ref: str) -> None:
        def stop() -> None:
            try:
                self._call(
                    self._data.stop_runtime_session,
                    idempotent=True,
                    agentRuntimeArn=self.runtime_arn,
                    qualifier=self.qualifier,
                    runtimeSessionId=provider_ref,
                )
            except Exception as error:
                if _error_code(error) != "ResourceNotFoundException":
                    raise

        # StopRuntimeSession returns once AgentCore has terminated the microVM.
        await _thread(stop)
        self._stopped.add(provider_ref)

    async def astop(self, handle: SandboxHandle) -> None:
        await self._stop(handle.provider_ref)

    async def adestroy(self, handle: SandboxHandle) -> None:
        # A stopped AgentCore session keeps nothing, so destroy and stop are the same.
        await self._stop(handle.provider_ref)


class AgentCoreCheckpointTransfer(_ArchiveTransfer):
    """Move checkpoints in and out of AgentCore microVMs through invocations.

    The in-computer server stops the agent's processes, archives /workspace and
    /runtime/native without excluded paths, and resumes them. The archives come
    out in chunks of at most 8 MiB and are validated and repacked here with the
    same code as Docker checkpoints. Restore fills an empty, unused generation and
    stops the computer if anything fails, so a partial restore never runs a turn.
    ``scratch`` holds unencrypted archives in transit and must be coordinator-private.
    """

    def __init__(
        self,
        provider: AgentCoreSandbox,
        store: CheckpointStore,
        *,
        archive: Optional[CheckpointArchive] = None,
        scratch: Optional[Path] = None,
    ) -> None:
        super().__init__(store, archive=archive, scratch=scratch)
        self.provider = provider

    async def _pull(self, handle: SandboxHandle, name: str, root: str, size: int, destination: Path) -> None:
        with destination.open("xb") as output:
            offset = 0
            while offset < size:
                reply = await _thread(
                    self.provider._invoke,
                    handle.provider_ref,
                    "get",
                    name=name,
                    root=root,
                    offset=offset,
                    length=_CHUNK,
                )
                data = base64.b64decode(reply["data"], validate=True)
                if not data:
                    raise SandboxError("Checkpoint export ended before its reported size")
                await _thread(output.write, data)
                offset += len(data)
        if offset != size:
            raise SandboxError("Checkpoint export changed size while it was read")

    async def _push(self, handle: SandboxHandle, name: str, root: str, source: Path) -> None:
        with source.open("rb") as stream:
            offset = 0
            while True:
                data = await _thread(stream.read, _CHUNK)
                if not data and offset:
                    return
                reply = await _thread(
                    self.provider._invoke,
                    handle.provider_ref,
                    "put",
                    name=name,
                    root=root,
                    offset=offset,
                    data=base64.b64encode(data).decode(),
                )
                offset += len(data)
                if reply["size"] != offset:
                    raise SandboxError("Checkpoint import size mismatch")
                if not data:
                    return

    async def acapture(
        self, handle: SandboxHandle, *, state: Mapping[str, Any], exclude: Sequence[str] = DEFAULT_NATIVE_EXCLUSIONS
    ) -> CheckpointRef:
        await self.provider._owned(handle)
        name = uuid4().hex
        exported = await _thread(
            self.provider._invoke,
            handle.provider_ref,
            "export",
            name=name,
            exclude=list(exclude),
            max_bytes=self.archive.limits.max_bytes,
        )
        try:
            with tempfile.TemporaryDirectory(prefix=".capture-", dir=self.scratch) as directory:
                root = Path(directory)
                exports = {}
                for part, size in exported["sizes"].items():
                    exports[part] = root / (part + ".tar")
                    await self._pull(handle, name, part, int(size), exports[part])
                await _thread(self._combine, exports, root / "checkpoint.tar", state, exclude)
                return await self.store.aput(root / "checkpoint.tar")
        finally:
            await asyncio.shield(_thread(self.provider._invoke, handle.provider_ref, "remove", name=name))

    async def arestore(self, handle: SandboxHandle, reference: CheckpointRef) -> Mapping[str, Any]:
        await self.provider._owned(handle)
        name = uuid4().hex
        with tempfile.TemporaryDirectory(prefix=".import-", dir=self.scratch) as directory:
            root = Path(directory)
            async with self.store.aopen_archive(reference) as checkpoint:
                state, native_mode = await _thread(self._split, checkpoint, root)
            try:
                for part in ("workspace", "native"):
                    await self._push(handle, name, part, root / (part + ".tar"))
                await _thread(self.provider._invoke, handle.provider_ref, "import", name=name, native_mode=native_mode)
            except BaseException:
                # A partially restored computer must never execute another turn.
                await asyncio.shield(self.provider.astop(handle))
                raise
        return state
