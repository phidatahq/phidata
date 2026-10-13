"""Docker execution for customer-operated trusted-team deployments."""

import asyncio
import base64
import hashlib
import json
import math
import os
import tempfile
from contextlib import suppress
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence

from agno.sandbox.base import ExecResult, Sandbox, SandboxError, SandboxHandle, _identity

_LABEL = "io.agno.sandbox."
_RUNNER = Path(__file__).with_name("_exec.py").read_text()


class DockerSandbox(Sandbox):
    """Linux/Python sandbox compute with explicit env and no host filesystem bind mounts.

    The Docker daemon is trusted infrastructure. Its socket is never mounted into
    the sandbox. Files are ephemeral tmpfs: stop/destroy requires an external
    checkpoint for recovery. This class alone is not a durable session service.
    """

    def __init__(
        self,
        image: str,
        *,
        namespace: str = "default",
        cpus: float = 2.0,
        memory_mb: int = 2048,
        pids_limit: int = 256,
        workspace_mb: int = 512,
        network: str = "none",
        docker_binary: str = "docker",
    ) -> None:
        for value in (image, namespace, network):
            if not isinstance(value, str) or not value or "\x00" in value:
                raise ValueError("Sandbox image, namespace and network must be nonempty strings")
        if image.startswith("-") or network == "host" or network.startswith("container:"):
            raise ValueError("Option-like images and shared host/container networking are not supported")
        if type(cpus) not in (int, float) or not math.isfinite(cpus) or cpus <= 0:
            raise ValueError("Sandbox CPU limit must be a positive number")
        if any(type(value) is not int or value < 1 for value in (memory_mb, pids_limit, workspace_mb)):
            raise ValueError("Sandbox memory, process and workspace limits must be positive integers")
        self.image = image
        self.namespace = namespace
        self.cpus = float(cpus)
        self.memory_mb = memory_mb
        self.pids_limit = pids_limit
        self.workspace_mb = workspace_mb
        self.network = network
        self.docker_binary = docker_binary

    def _name(self, session_id: str, agent_id: Optional[str], generation: int) -> str:
        identity = json.dumps([self.namespace, agent_id, session_id, generation])
        return "agno-" + hashlib.sha256(identity.encode()).hexdigest()[:40]

    def _digest(self, session_id: str, agent_id: Optional[str], generation: int, env: Mapping[str, str]) -> str:
        data = {
            "image": self.image,
            "cpus": self.cpus,
            "memory_mb": self.memory_mb,
            "pids_limit": self.pids_limit,
            "workspace_mb": self.workspace_mb,
            "network": self.network,
            "agent_id": agent_id,
            "session_id": session_id,
            "generation": generation,
            "env": dict(env),
            "storage": "managed-tmpfs-v1",
        }
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
                agent_id=labels[_LABEL + "agent"] or None,
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
        digest = self._digest(session_id, agent_id, generation, values)
        current = await self.aget(name)
        if current is None:
            labels = {
                "namespace": self.namespace,
                "agent": agent_id or "",
                "session": session_id,
                "generation": str(generation),
                "config": digest,
            }
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
                self.network,
                "--memory",
                f"{self.memory_mb}m",
                "--memory-swap",
                f"{self.memory_mb}m",
                "--cpus",
                str(self.cpus),
                "--pids-limit",
                str(self.pids_limit),
                "--mount",
                f"type=volume,source={name}-workspace,target=/workspace,volume-nocopy",
                "--mount",
                f"type=volume,source={name}-runtime,target=/runtime,volume-nocopy",
                "--tmpfs",
                "/tmp:rw,nosuid,nodev,uid=1000,gid=1000,mode=1777,size=128m",
                "--workdir",
                "/workspace",
            ]
            for key, value in labels.items():
                args.extend(["--label", _LABEL + key + "=" + value])
            # Env values go through a private file so they never appear in the host process list.
            env_file = self._write_env_file({"HOME": "/runtime", **values})
            args.extend(["--env-file", env_file])
            args.extend(["--entrypoint", "python", self.image, "-I", "-c", "import time; time.sleep(2147483647)"])
            try:
                await self._ensure_volume(
                    name + "-workspace",
                    self._volume_labels(session_id, agent_id, generation, digest, "workspace"),
                    self.workspace_mb,
                )
                await self._ensure_volume(
                    name + "-runtime", self._volume_labels(session_id, agent_id, generation, digest, "runtime"), 256
                )
                try:
                    code, _, err = await self._docker(*args, timeout=120)
                except asyncio.TimeoutError:
                    code, err = 1, b"Creation response timed out"
                # A concurrent creator or lost response is resolved by the deterministic name.
                current = await self.aget(name)
                if current is None:
                    raise SandboxError("Docker creation failed: " + err.decode(errors="replace")[:500])
            except Exception:
                # Unmounted volumes would block a corrected configuration for this generation; Docker keeps in-use ones.
                with suppress(Exception):
                    await self._delete_volumes(name, session_id, agent_id, generation, digest)
                raise
            finally:
                # The env file holds credentials, so remove it however volume setup or creation ends.
                with suppress(FileNotFoundError):
                    os.unlink(env_file)
        if current.config_digest != digest:
            raise SandboxError("Sandbox generation already exists with different configuration")
        if current.state == "paused":
            # Pause cannot tell an interrupted capture from a partial restore, so never resume implicitly.
            raise SandboxError(
                "Sandbox generation is paused by an interrupted checkpoint transfer; reconcile it before reuse"
            )
        if current.state == "created":
            code, _, err = await self._docker("container", "start", current.provider_ref)
            current = await self.aget(current.provider_ref)
            if code and (current is None or current.state != "running"):
                # A container that never ran holds no files; remove it so the caller is not left an orphan.
                if current is not None and current.state == "created":
                    await self._docker("container", "rm", current.provider_ref)
                    with suppress(Exception):
                        await self._delete_volumes(name, session_id, agent_id, generation, digest)
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

    def _volume_labels(
        self, session_id: str, agent_id: Optional[str], generation: int, config: str, role: str
    ) -> Dict[str, str]:
        labels = {
            "namespace": self.namespace,
            "agent": agent_id or "",
            "session": session_id,
            "generation": str(generation),
            "config": config,
            "role": role,
        }
        return {_LABEL + key: value for key, value in labels.items()}

    async def _ensure_volume(self, name: str, expected: Dict[str, str], size_mb: int) -> None:
        options = {
            "type": "tmpfs",
            "device": "tmpfs",
            "o": f"rw,nosuid,nodev,size={size_mb}m,uid=1000,gid=1000,mode=0700",
        }
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

    async def _delete_volumes(
        self, prefix: str, session_id: str, agent_id: Optional[str], generation: int, config: str
    ) -> None:
        for role in ("workspace", "runtime"):
            name = prefix + "-" + role
            current = await self._volume(name)
            if current is None:
                continue
            labels = current.get("Labels") or {}
            expected = self._volume_labels(session_id, agent_id, generation, config, role)
            if any(labels.get(key) != value for key, value in expected.items()):
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
        await self._delete_volumes(
            handle.name, handle.session_id, handle.agent_id, handle.generation, handle.config_digest
        )
