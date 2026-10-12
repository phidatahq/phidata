"""Docker execution for customer-operated trusted-team deployments."""

import asyncio
import hashlib
import json
import math
import os
import tempfile
from contextlib import suppress
from dataclasses import fields
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from agno.sandbox.base import ExecResult, SandboxError, SandboxHandle, SandboxProvider, SandboxSpec

_LABEL = "io.agno.sandbox."
_RUNNER = Path(__file__).with_name("_exec.py").read_text()


class DockerSandboxProvider(SandboxProvider):
    """Linux/Python sandbox compute with explicit env and no host filesystem mounts.

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
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()

    @staticmethod
    def _write_env_file(env: Mapping[str, str]) -> str:
        for key, value in env.items():
            if key[0] == "#" or any(char.isspace() for char in key) or "\n" in value or "\r" in value:
                raise ValueError(
                    "Docker sandbox env names cannot contain whitespace or start with '#'; values cannot contain newlines"
                )
        descriptor, path = tempfile.mkstemp(prefix="agno-sandbox-env-")
        with os.fdopen(descriptor, "w", encoding="utf-8") as file:
            file.writelines(key + "=" + value + "\n" for key, value in env.items())
        return path

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
            or current.agent_id != handle.agent_id
            or current.session_id != handle.session_id
            or current.generation != handle.generation
            or current.config_digest != handle.config_digest
        ):
            raise SandboxError("Sandbox identity changed; refusing the operation")
        return current

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
            args = [
                "container",
                "create",
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
                "--tmpfs",
                f"/workspace:rw,nosuid,nodev,uid=1000,gid=1000,mode=0700,size={spec.workspace_mb}m",
                "--tmpfs",
                "/runtime:rw,nosuid,nodev,uid=1000,gid=1000,mode=0700,size=256m",
                "--tmpfs",
                "/tmp:rw,nosuid,nodev,uid=1000,gid=1000,mode=1777,size=128m",
                "--workdir",
                "/workspace",
            ]
            for key, value in labels.items():
                args.extend(["--label", _LABEL + key + "=" + value])
            # Env values go through a private file so they never appear in the host process list.
            env_file = self._write_env_file({"HOME": "/runtime", **spec.env})
            args.extend(["--env-file", env_file])
            args.extend(["--entrypoint", "python", spec.image, "-I", "-c", "import time; time.sleep(2147483647)"])
            try:
                code, _, err = await self._docker(*args, timeout=120)
            except asyncio.TimeoutError:
                code, err = 1, b"Creation response timed out"
            finally:
                with suppress(FileNotFoundError):
                    os.unlink(env_file)
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
                # A container that never ran holds no files; remove it so the caller is not left an orphan.
                if current is not None and current.state == "created":
                    await self._docker("container", "rm", current.provider_ref)
                raise SandboxError("Docker start failed: " + err.decode(errors="replace")[:500])
        if current is None or current.state != "running":
            raise SandboxError("Sandbox generation is not running; recovery requires a new generation")
        return current

    async def aexec(
        self, handle: SandboxHandle, argv: Sequence[str], *, timeout: float = 60, max_output_bytes: int = 1_048_576
    ) -> ExecResult:
        if isinstance(argv, (str, bytes)) or not argv or any(not isinstance(arg, str) or "\x00" in arg for arg in argv):
            raise ValueError("Commands must be a nonempty sequence of strings")
        if not math.isfinite(timeout) or timeout <= 0 or not 1 <= max_output_bytes <= 4 * 1024 * 1024:
            raise ValueError("Timeout must be positive and output limit must be between 1 byte and 4 MiB")
        current = await self._owned(handle)
        if current is None or current.state != "running":
            raise SandboxError("Sandbox is not running")
        request = json.dumps({"argv": list(argv), "timeout": timeout, "max_output_bytes": max_output_bytes}).encode()
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
            await asyncio.shield(self.astop(handle))
            raise
        if code:
            await self.astop(handle)
            raise SandboxError("Sandbox command transport failed: " + err.decode(errors="replace")[:500])
        try:
            result = ExecResult(**json.loads(out))
            if result.timed_out or result.output_limited:
                await self.astop(handle)
            return result
        except (TypeError, ValueError) as error:
            await self.astop(handle)
            raise SandboxError("Sandbox returned an invalid command result") from error

    async def astop(self, handle: SandboxHandle) -> None:
        current = await self._owned(handle)
        if current is None or current.state in ("exited", "dead", "created"):
            return
        code, _, err = await self._docker("container", "stop", "--time", "2", handle.provider_ref, timeout=15)
        if code:
            raise SandboxError("Docker stop failed: " + err.decode(errors="replace")[:500])

    async def adestroy(self, handle: SandboxHandle) -> None:
        if await self._owned(handle) is None:
            return
        code, _, err = await self._docker("container", "rm", "--force", handle.provider_ref)
        if code and b"already in progress" in err:
            for _ in range(50):
                if await self._owned(handle) is None:
                    return
                await asyncio.sleep(0.1)
        if code and await self._owned(handle) is not None:
            raise SandboxError("Docker removal failed: " + err.decode(errors="replace")[:500])
