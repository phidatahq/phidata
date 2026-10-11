"""Docker execution for customer-operated trusted-team deployments."""

import asyncio
import base64
import hashlib
import json
import math
from contextlib import suppress
from dataclasses import fields
from pathlib import Path
from typing import Any, Optional, Sequence

from agno.sandbox.base import ExecResult, SandboxError, SandboxHandle, SandboxProvider, SandboxSpec

_LABEL = "io.agno.sandbox."
_RUNNER = Path(__file__).with_name("_exec.py").read_text()


class DockerSandboxProvider(SandboxProvider):
    """Linux/Python sandbox compute with explicit env and no host filesystem bind mounts.

    The Docker daemon is trusted infrastructure. Its socket is never mounted into
    the sandbox. Files are ephemeral tmpfs: stop/destroy requires an external
    checkpoint for recovery. This class alone is not a durable session service.
    """

    def __init__(self, namespace: str, *, docker_binary: str = "docker") -> None:
        if not namespace or "\x00" in namespace:
            raise ValueError("A nonempty deployment namespace is required")
        self.namespace = namespace
        self.docker_binary = docker_binary

    def _name(self, spec: SandboxSpec) -> str:
        identity = json.dumps([self.namespace, spec.agent_id, spec.session_id, spec.generation])
        return "agno-" + hashlib.sha256(identity.encode()).hexdigest()[:40]

    @staticmethod
    def _digest(spec: SandboxSpec) -> str:
        data = {item.name: getattr(spec, item.name) for item in fields(spec)}
        data["env"] = dict(spec.env)
        data["storage"] = "managed-tmpfs-v1"
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()

    async def _docker(
        self, *args: str, input_data: Optional[bytes] = None, timeout: float = 30
    ) -> tuple[int, bytes, bytes]:
        process = await asyncio.create_subprocess_exec(
            self.docker_binary,
            *args,
            stdin=asyncio.subprocess.PIPE if input_data is not None else asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        async def read(stream: Any) -> bytes:
            chunks = []
            size = 0
            while chunk := await stream.read(65536):
                size += len(chunk)
                if size > 32 * 1024 * 1024:
                    raise SandboxError("Docker response exceeded the transport output limit")
                chunks.append(chunk)
            return b"".join(chunks)

        async def send() -> None:
            if process.stdin is not None:
                try:
                    process.stdin.write(input_data or b"")
                    await process.stdin.drain()
                except (BrokenPipeError, ConnectionResetError):
                    pass
                finally:
                    process.stdin.close()

        tasks = [
            asyncio.create_task(read(process.stdout)),
            asyncio.create_task(read(process.stderr)),
            asyncio.create_task(send()),
        ]
        try:
            results = await asyncio.wait_for(asyncio.gather(*tasks), timeout)
            await asyncio.wait_for(process.wait(), 5)
            assert isinstance(results[0], bytes) and isinstance(results[1], bytes)
            return process.returncode or 0, results[0], results[1]
        except BaseException:
            if process.returncode is None:
                with suppress(ProcessLookupError):
                    process.kill()
            await process.wait()
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            raise

    async def aget(self, provider_ref: str) -> Optional[SandboxHandle]:
        if not provider_ref or provider_ref.startswith("-") or "\x00" in provider_ref:
            raise ValueError("Invalid Docker sandbox reference")
        code, out, err = await self._docker("container", "inspect", provider_ref)
        if code:
            if b"No such container" in err or b"No such object" in err:
                return None
            raise SandboxError("Docker inspection failed: " + err.decode(errors="replace")[:500])
        record = json.loads(out)[0]
        labels = record.get("Config", {}).get("Labels") or {}
        if labels.get(_LABEL + "namespace") != self.namespace:
            raise SandboxError("Container does not belong to this sandbox namespace")
        try:
            return SandboxHandle(
                provider_ref=record["Id"],
                name=record["Name"].lstrip("/"),
                agent_id=labels[_LABEL + "agent"],
                session_id=labels[_LABEL + "session"],
                generation=int(labels[_LABEL + "generation"]),
                state=record["State"]["Status"],
                config_digest=labels[_LABEL + "config"],
            )
        except (KeyError, TypeError, ValueError) as error:
            raise SandboxError("Container has incomplete sandbox identity labels") from error

    async def _owned(self, handle: SandboxHandle) -> Optional[SandboxHandle]:
        current = await self.aget(handle.provider_ref)
        if current is not None and (
            current.provider_ref != handle.provider_ref
            or current.name != handle.name
            or current.agent_id != handle.agent_id
            or current.session_id != handle.session_id
            or current.generation != handle.generation
            or current.config_digest != handle.config_digest
        ):
            raise SandboxError("Sandbox identity changed; refusing the operation")
        return current

    async def afind(self, spec: SandboxSpec) -> Optional[SandboxHandle]:
        handle = await self.aget(self._name(spec))
        if handle is not None and handle.config_digest != self._digest(spec):
            raise SandboxError("Existing generation has different compute configuration")
        return handle

    async def acreate(self, spec: SandboxSpec) -> SandboxHandle:
        name, digest = self._name(spec), self._digest(spec)
        current = await self.aget(name)
        if current is None:
            labels = {
                "namespace": self.namespace,
                "agent": spec.agent_id,
                "session": spec.session_id,
                "generation": str(spec.generation),
                "config": digest,
            }
            await self._ensure_volume(name + "-workspace", labels, "workspace", spec.workspace_mb)
            await self._ensure_volume(name + "-runtime", labels, "runtime", 256)
            args = [
                "container",
                "create",
                "--init",
                "--name",
                name,
                "--user",
                "1000:1000",
                "--read-only",
                "--cap-drop",
                "ALL",
                "--security-opt",
                "no-new-privileges",
                "--network",
                spec.network,
                "--memory",
                f"{spec.memory_mb}m",
                "--memory-swap",
                f"{spec.memory_mb}m",
                "--cpus",
                str(spec.cpus),
                "--pids-limit",
                str(spec.pids_limit),
                "--mount",
                f"type=volume,source={name}-workspace,target=/workspace,volume-nocopy",
                "--mount",
                f"type=volume,source={name}-runtime,target=/runtime,volume-nocopy",
                "--tmpfs",
                "/tmp:rw,nosuid,nodev,uid=1000,gid=1000,mode=1777,size=128m",
                "--workdir",
                "/workspace",
                "--env",
                "HOME=/runtime",
            ]
            for key, value in labels.items():
                args.extend(["--label", _LABEL + key + "=" + value])
            for key, value in spec.env.items():
                args.extend(["--env", key + "=" + value])
            args.extend(["--entrypoint", "python", spec.image, "-I", "-c", "import time; time.sleep(2147483647)"])
            try:
                code, _, err = await self._docker(*args, timeout=120)
            except asyncio.TimeoutError:
                code, err = 1, b"Creation response timed out"
            # A concurrent creator or lost response is resolved by the deterministic name.
            current = await self.aget(name)
            if current is None:
                raise SandboxError("Docker creation failed: " + err.decode(errors="replace")[:500])
        if current.config_digest != digest:
            raise SandboxError("Sandbox generation already exists with different configuration")
        if current.state == "created":
            code, _, err = await self._docker("container", "start", current.provider_ref)
            current = await self.aget(current.provider_ref)
            if code and (current is None or current.state != "running"):
                raise SandboxError("Docker start failed: " + err.decode(errors="replace")[:500])
        if current is None or current.state != "running":
            raise SandboxError("Sandbox generation is not running; recovery requires a new generation")
        return current

    async def aexec(
        self,
        handle: SandboxHandle,
        argv: Sequence[str],
        *,
        timeout: float = 60,
        max_output_bytes: int = 1_048_576,
        stdin: bytes = b"",
    ) -> ExecResult:
        return await self._aexec(handle, argv, timeout=timeout, max_output_bytes=max_output_bytes, stdin=stdin)

    async def arpc(self, handle: SandboxHandle, operation: str, payload: bytes) -> ExecResult:
        if operation not in ("start", "poll") or not isinstance(payload, bytes) or len(payload) > 1024 * 1024:
            raise ValueError("Runtime RPC requires start/poll and a payload no larger than 1 MiB")
        return await self._aexec(
            handle,
            ["python", "-I", "-m", "agno.sandbox.runtime", operation],
            timeout=15,
            max_output_bytes=4 * 1024 * 1024,
            stdin=payload,
            stop_on_failure=False,
        )

    async def _aexec(
        self,
        handle: SandboxHandle,
        argv: Sequence[str],
        *,
        timeout: float = 60,
        max_output_bytes: int = 1_048_576,
        stdin: bytes = b"",
        stop_on_failure: bool = True,
    ) -> ExecResult:
        if isinstance(argv, (str, bytes)) or not argv or any(not isinstance(arg, str) or "\x00" in arg for arg in argv):
            raise ValueError("Commands must be a nonempty sequence of strings")
        if not math.isfinite(timeout) or timeout <= 0 or not 1 <= max_output_bytes <= 4 * 1024 * 1024:
            raise ValueError("Timeout must be positive and output limit must be between 1 byte and 4 MiB")
        if not isinstance(stdin, bytes) or len(stdin) > 8 * 1024 * 1024:
            raise ValueError("Command stdin must be bytes no larger than 8 MiB")
        current = await self._owned(handle)
        if current is None or current.state != "running":
            raise SandboxError("Sandbox is not running")
        request = json.dumps(
            {
                "argv": list(argv),
                "timeout": timeout,
                "max_output_bytes": max_output_bytes,
                "stdin": base64.b64encode(stdin).decode("ascii"),
            }
        ).encode()
        try:
            code, out, err = await self._docker(
                "container",
                "exec",
                "-i",
                handle.provider_ref,
                "python",
                "-I",
                "-c",
                _RUNNER,
                input_data=request,
                timeout=timeout + 15,
            )
        except (asyncio.CancelledError, asyncio.TimeoutError, SandboxError):
            # Killing the Docker client does not kill its remote command. Stop compute
            # to bound cancellation; checkpoint recovery belongs to the coordinator.
            if stop_on_failure:
                await asyncio.shield(self.astop(handle))
            raise
        if code:
            if stop_on_failure:
                await self.astop(handle)
            raise SandboxError("Sandbox command transport failed: " + err.decode(errors="replace")[:500])
        try:
            result = ExecResult(**json.loads(out))
            if stop_on_failure and (result.timed_out or result.output_limited):
                await self.astop(handle)
            return result
        except (TypeError, ValueError) as error:
            if stop_on_failure:
                await self.astop(handle)
            raise SandboxError("Sandbox returned an invalid command result") from error

    async def astop(self, handle: SandboxHandle) -> None:
        current = await self._owned(handle)
        if current is None or current.state in ("exited", "dead", "created"):
            return
        if current.state == "paused":
            code, _, err = await self._docker("container", "unpause", handle.provider_ref)
            if code:
                raise SandboxError("Docker could not unpause before stop: " + err.decode(errors="replace")[:500])
        code, _, err = await self._docker("container", "stop", "--time", "2", handle.provider_ref, timeout=15)
        if code:
            raise SandboxError("Docker stop failed: " + err.decode(errors="replace")[:500])

    async def _volume(self, name: str) -> Optional[Any]:
        code, out, err = await self._docker("volume", "inspect", name)
        if code:
            if b"no such volume" in err.lower():
                return None
            raise SandboxError("Docker volume inspection failed: " + err.decode(errors="replace")[:500])
        return json.loads(out)[0]

    async def _ensure_volume(self, name: str, labels: Any, role: str, size_mb: int) -> None:
        options = {
            "type": "tmpfs",
            "device": "tmpfs",
            "o": f"rw,nosuid,nodev,size={size_mb}m,uid=1000,gid=1000,mode=0700",
        }
        expected = {_LABEL + key: value for key, value in {**labels, "role": role}.items()}
        current = await self._volume(name)
        if current is None:
            args = ["volume", "create", "--driver", "local"]
            for key, value in options.items():
                args.extend(["--opt", key + "=" + value])
            for key, value in expected.items():
                args.extend(["--label", key + "=" + value])
            args.append(name)
            try:
                await self._docker(*args)
            except asyncio.TimeoutError:
                pass  # Resolve a lost create response through the deterministic name.
            current = await self._volume(name)
        if (
            current is None
            or current.get("Driver") != "local"
            or current.get("Options") != options
            or any((current.get("Labels") or {}).get(key) != value for key, value in expected.items())
        ):
            raise SandboxError("Docker volume identity or storage configuration mismatch")

    async def _delete_volumes(self, handle: SandboxHandle) -> None:
        for role in ("workspace", "runtime"):
            name = handle.name + "-" + role
            current = await self._volume(name)
            if current is None:
                continue
            labels = current.get("Labels") or {}
            expected = {
                "namespace": self.namespace,
                "agent": handle.agent_id,
                "session": handle.session_id,
                "generation": str(handle.generation),
                "config": handle.config_digest,
                "role": role,
            }
            if any(labels.get(_LABEL + key) != value for key, value in expected.items()):
                raise SandboxError("Refusing to remove a volume with a different sandbox identity")
            code, _, err = await self._docker("volume", "rm", name)
            if code and await self._volume(name) is not None:
                raise SandboxError("Docker volume removal failed: " + err.decode(errors="replace")[:500])

    async def adestroy(self, handle: SandboxHandle) -> None:
        if await self._owned(handle) is not None:
            code, _, err = await self._docker("container", "rm", "--force", handle.provider_ref)
            if code and b"already in progress" in err:
                for _ in range(50):
                    if await self._owned(handle) is None:
                        break
                    await asyncio.sleep(0.1)
            if code and await self._owned(handle) is not None:
                raise SandboxError("Docker removal failed: " + err.decode(errors="replace")[:500])
        # Also reconcile a lost removal response after the container is already gone.
        await self._delete_volumes(handle)
