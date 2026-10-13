"""Small sandbox contract; ownership and durable completion belong to AgentOS."""

import asyncio
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Coroutine, Dict, Mapping, Optional, Sequence


class SandboxError(RuntimeError):
    """A sandbox operation failed; callers must reconcile uncertain execution outcomes."""


def _identity(
    session_id: str, agent_id: Optional[str], generation: int, env: Optional[Mapping[str, str]]
) -> Dict[str, str]:
    """Validate per-session create arguments and return a copy of env."""
    if not isinstance(session_id, str) or not session_id or "\x00" in session_id:
        raise ValueError("Sandbox session id must be a nonempty string")
    if agent_id is not None and (not isinstance(agent_id, str) or not agent_id or "\x00" in agent_id):
        raise ValueError("Sandbox agent id must be None or a nonempty string")
    if type(generation) is not int or generation < 1:
        raise ValueError("Sandbox generation must be a positive integer")
    values = dict(env or {})
    for key, value in values.items():
        if (
            not isinstance(key, str)
            or not key
            or "=" in key
            or "\x00" in key
            or not isinstance(value, str)
            or "\x00" in value
        ):
            raise ValueError("Sandbox environment must contain valid names and string values")
    return values


@dataclass(frozen=True)
class SandboxHandle:
    provider_ref: str
    name: str
    agent_id: Optional[str]
    session_id: str
    generation: int
    state: str
    config_digest: str


@dataclass(frozen=True)
class ExecResult:
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool = False
    output_limited: bool = False


def _sync(coro: Coroutine[Any, Any, Any]) -> Any:
    # Inside a running loop (notebook, async server) run on a worker thread with its own loop.
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result()


class Sandbox(ABC):
    """A backend for compute, without queue ownership or checkpoint policy.

    Implementations must not retry uncertain commands. Pause and resume are the
    optional warm path: a paused sandbox keeps its files and memory and the same
    generation resumes it, so a later turn on the same session need not restore a
    checkpoint. Stop and destroy remain the cold path, after which recovery needs a
    new generation. Snapshot, preview and nested-container features are not implied.
    """

    @abstractmethod
    async def acreate(
        self,
        session_id: str,
        *,
        agent_id: Optional[str] = None,
        generation: int = 1,
        env: Optional[Mapping[str, str]] = None,
    ) -> SandboxHandle: ...

    def create(
        self,
        session_id: str,
        *,
        agent_id: Optional[str] = None,
        generation: int = 1,
        env: Optional[Mapping[str, str]] = None,
    ) -> SandboxHandle:
        return _sync(self.acreate(session_id, agent_id=agent_id, generation=generation, env=env))

    @abstractmethod
    async def aget(self, provider_ref: str) -> Optional[SandboxHandle]: ...

    def get(self, provider_ref: str) -> Optional[SandboxHandle]:
        return _sync(self.aget(provider_ref))

    @abstractmethod
    async def aexec(
        self,
        handle: SandboxHandle,
        argv: Sequence[str],
        *,
        timeout: float = 60,
        max_output_bytes: int = 1_048_576,
        stdin: bytes = b"",
    ) -> ExecResult: ...

    def exec(
        self,
        handle: SandboxHandle,
        argv: Sequence[str],
        *,
        timeout: float = 60,
        max_output_bytes: int = 1_048_576,
        stdin: bytes = b"",
    ) -> ExecResult:
        return _sync(self.aexec(handle, argv, timeout=timeout, max_output_bytes=max_output_bytes, stdin=stdin))

    @abstractmethod
    async def astop(self, handle: SandboxHandle) -> None: ...

    def stop(self, handle: SandboxHandle) -> None:
        _sync(self.astop(handle))

    @abstractmethod
    async def adestroy(self, handle: SandboxHandle) -> None: ...

    def destroy(self, handle: SandboxHandle) -> None:
        _sync(self.adestroy(handle))

    async def apause(self, handle: SandboxHandle) -> None:
        """Freeze a running sandbox, keeping its files, memory and processes.

        The warm path between turns: nothing is lost and nothing needs restoring.
        Providers without a native pause leave this unimplemented; the caller then
        keeps the sandbox running or takes the cold path.
        """
        raise NotImplementedError("This provider does not support pausing compute")

    def pause(self, handle: SandboxHandle) -> None:
        _sync(self.apause(handle))

    async def aresume(self, handle: SandboxHandle) -> SandboxHandle:
        """Unfreeze a paused sandbox and return its running handle.

        Only a paused sandbox resumes. A stopped one has lost its files and must be
        recovered into a new generation from a checkpoint.
        """
        raise NotImplementedError("This provider does not support resuming compute")

    def resume(self, handle: SandboxHandle) -> SandboxHandle:
        return _sync(self.aresume(handle))
