"""Small execution-provider contract; ownership and durable completion belong to AgentOS."""

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Coroutine, Mapping, Optional, Sequence


class SandboxError(RuntimeError):
    """A sandbox operation failed; callers must reconcile uncertain execution outcomes."""


@dataclass(frozen=True)
class SandboxSpec:
    agent_id: str
    session_id: str
    generation: int
    image: str
    env: Mapping[str, str] = field(default_factory=dict, repr=False)
    cpus: float = 2.0
    memory_mb: int = 2048
    pids_limit: int = 256
    workspace_mb: int = 512
    network: str = "none"

    def __post_init__(self) -> None:
        for value in (self.agent_id, self.session_id, self.image, self.network):
            if not isinstance(value, str) or not value or "\x00" in value:
                raise ValueError("Sandbox identity, image and network must be nonempty strings")
        if self.image.startswith("-") or self.network == "host" or self.network.startswith("container:"):
            raise ValueError("Option-like images and shared host/container networking are not supported")
        if type(self.generation) is not int or self.generation < 1 or not math.isfinite(self.cpus) or self.cpus <= 0:
            raise ValueError("Sandbox generation and CPU limit must be positive")
        if any(type(value) is not int or value < 1 for value in (self.memory_mb, self.pids_limit, self.workspace_mb)):
            raise ValueError("Sandbox memory, process and workspace limits must be positive")
        values = dict(self.env)
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
        object.__setattr__(self, "env", MappingProxyType(values))


@dataclass(frozen=True)
class SandboxHandle:
    provider_ref: str
    name: str
    agent_id: str
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
    from agno.agents.base import run_coroutine_sync

    return run_coroutine_sync(coro)


class SandboxProvider(ABC):
    """A backend for compute, without queue ownership or checkpoint policy.

    Implementations must not retry uncertain commands. Optional snapshot, pause,
    preview and nested-container features are not implied by this interface.
    """

    @abstractmethod
    async def acreate(self, spec: SandboxSpec) -> SandboxHandle: ...

    def create(self, spec: SandboxSpec) -> SandboxHandle:
        return _sync(self.acreate(spec))

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

    async def arpc(self, handle: SandboxHandle, operation: str, payload: bytes) -> ExecResult:
        """Send a bounded runtime start/poll request without terminating session compute.

        A lost response is an uncertain control request, not a cancellation of the
        model turn. Providers supporting session runtimes implement this separately
        from arbitrary shell execution and must not replay a different execution.
        """
        raise NotImplementedError("This provider does not implement the runtime control protocol")

    def rpc(self, handle: SandboxHandle, operation: str, payload: bytes) -> ExecResult:
        return _sync(self.arpc(handle, operation, payload))

    @abstractmethod
    async def astop(self, handle: SandboxHandle) -> None: ...

    def stop(self, handle: SandboxHandle) -> None:
        _sync(self.astop(handle))

    @abstractmethod
    async def adestroy(self, handle: SandboxHandle) -> None: ...

    def destroy(self, handle: SandboxHandle) -> None:
        _sync(self.adestroy(handle))
