"""Shared ownership and transport rules for explicit hosted provider adapters."""

import asyncio
import base64
import hashlib
import json
import math
from abc import abstractmethod
from dataclasses import asdict, dataclass
from typing import Any, Dict, Mapping, Optional, Sequence
from uuid import uuid4

from agno.sandbox.allocation import PostgresAllocationJournal, SandboxAllocationUnknown
from agno.sandbox.base import ExecResult, SandboxError, SandboxHandle, SandboxProvider, SandboxSpec


@dataclass(frozen=True)
class HostedComputer:
    provider_ref: str
    metadata: Mapping[str, str]
    state: str


async def _drain(awaitable: Any) -> Any:
    task = asyncio.ensure_future(awaitable)
    try:
        return await asyncio.shield(task)
    except asyncio.CancelledError:
        try:
            await task
        finally:
            raise


class HostedSandboxProvider(SandboxProvider):
    """Ownership, capacity and root transport shared by hosted implementations.

    Providers must supply authoritative identity/inventory and permanently stop
    compute on deletion. SDK retries must preserve a provider-enforced idempotency identity;
    uncertain operations must never be sent as a new execution. Prepared images must contain this package at a root-owned location.
    Hosted disk/PID controls are provider defaults; checkpoint limits are separate.
    """

    backend = "abstract"

    def __init__(
        self, namespace: str, journal: PostgresAllocationJournal, *, max_allocations: int = 10, lifetime: int = 1800
    ) -> None:
        if not namespace or len(namespace) > 90 or type(max_allocations) is not int or max_allocations < 1:
            raise ValueError("Hosted namespace and allocation capacity must be bounded and nonempty")
        if type(lifetime) is not int or lifetime < 60:
            raise ValueError("Hosted lifetime must be at least 60 seconds")
        self.namespace = self.backend + ":" + namespace
        self.journal, self.max_allocations, self.lifetime = journal, max_allocations, lifetime

    def _validate_spec(self, spec: SandboxSpec) -> None:
        if spec.pids_limit is not None or spec.workspace_mb is not None:
            raise ValueError("Hosted providers require explicit pids_limit=None and workspace_mb=None")
        if spec.network not in ("none", "internet"):
            raise ValueError("Hosted network must be none or internet")

    def _name(self, spec: SandboxSpec) -> str:
        identity = [self.namespace, spec.agent_id, spec.session_id, spec.generation]
        return "agno-" + hashlib.sha256(json.dumps(identity).encode()).hexdigest()[:40]

    def _digest(self, spec: SandboxSpec) -> str:
        values = {key: getattr(spec, key) for key in spec.__dataclass_fields__}
        values["env"] = dict(spec.env)
        values.update(namespace=self.namespace, lifetime=self.lifetime)
        return hashlib.sha256(json.dumps(values, sort_keys=True, allow_nan=False).encode()).hexdigest()

    def _metadata(self, spec: SandboxSpec, token: str) -> Dict[str, str]:
        return dict(
            namespace=self.namespace,
            name=self._name(spec),
            agent=spec.agent_id,
            session=spec.session_id,
            generation=str(spec.generation),
            config=self._digest(spec),
            token=token,
        )

    def _handle(self, computer: HostedComputer) -> SandboxHandle:
        metadata = computer.metadata
        if metadata.get("namespace") != self.namespace:
            raise SandboxError("Hosted computer belongs to a different namespace")
        try:
            return SandboxHandle(
                computer.provider_ref,
                metadata["name"],
                metadata["agent"],
                metadata["session"],
                int(metadata["generation"]),
                computer.state,
                metadata["config"],
            )
        except (KeyError, TypeError, ValueError) as error:
            raise SandboxError("Hosted computer has incomplete ownership metadata") from error

    async def _verify(self, computer: HostedComputer) -> SandboxHandle:
        handle = self._handle(computer)
        row = await self.journal.ainspect(self.namespace, handle.name)
        if (
            row is None
            or row["state"] != "ready"
            or row["token"] != computer.metadata.get("token")
            or row["provider_ref"] != handle.provider_ref
            or row["digest"] != handle.config_digest
        ):
            raise SandboxAllocationUnknown("Provider identity does not match its durable allocation")
        return handle

    async def afind(self, spec: SandboxSpec) -> Optional[SandboxHandle]:
        self._validate_spec(spec)
        row = await self.journal.ainspect(self.namespace, self._name(spec))
        if row is None or row["state"] == "retired":
            return None
        if row["digest"] != self._digest(spec):
            raise SandboxError("Allocation generation configuration changed")
        if row["provider_ref"] is None:
            matches = await _drain(self._inventory(row["token"]))
            if len(matches) != 1:
                raise SandboxAllocationUnknown("Pending create requires exactly one matching provider allocation")
            computer = matches[0]
            if dict(computer.metadata) != self._metadata(spec, row["token"]):
                raise SandboxAllocationUnknown("Reconciled allocation metadata differs from the requested generation")
            await self.journal._bind(self.namespace, row["name"], row["token"], computer.provider_ref)
        else:
            computer = await _drain(self._get(row["provider_ref"]))
            if computer is None:
                await self.journal._retire(self.namespace, row["name"], row["token"], row["provider_ref"])
                return None
        return await self._verify(computer)

    async def acreate(self, spec: SandboxSpec) -> SandboxHandle:
        self._validate_spec(spec)
        existing = await self.afind(spec)
        if existing is not None:
            if existing.state != "running":
                raise SandboxError("Hosted generation is stopped; restore into a new generation")
            computer = await _drain(self._get(existing.provider_ref))
            if computer is None:
                raise SandboxError("Hosted computer disappeared during reconciliation")
            await self._check_resources(spec, computer)
            await self._control(existing, "init", {})
            return existing
        row, owner = await self.journal._reserve(
            self.namespace, self._name(spec), self._digest(spec), max_allocations=self.max_allocations
        )
        if not owner:
            raise SandboxAllocationUnknown("Another replica owns this allocation intent; reconcile before retrying")
        computer = await _drain(self._create(spec, self._metadata(spec, row["token"])))
        # Bind before doing further work so a failed initialization is still
        # visible and reclaimable by a replacement coordinator.
        await self.journal._bind(self.namespace, row["name"], row["token"], computer.provider_ref)
        handle = await self._verify(computer)
        if dict(computer.metadata) != self._metadata(spec, row["token"]):
            raise SandboxAllocationUnknown("Created computer has unexpected ownership metadata")
        try:
            if computer.state != "running":
                raise SandboxError("Created hosted computer is not running")
            await self._check_resources(spec, computer)
            await self._control(handle, "init", {})
        except BaseException:
            await _drain(self.adestroy(handle))
            raise
        return handle

    async def aget(self, provider_ref: str) -> Optional[SandboxHandle]:
        computer = await _drain(self._get(provider_ref))
        return None if computer is None else await self._verify(computer)

    async def _owned(self, handle: SandboxHandle, *, running: bool = False) -> Optional[SandboxHandle]:
        current = await self.aget(handle.provider_ref)
        if current is not None:
            expected, actual = asdict(handle), asdict(current)
            expected.pop("state")
            actual.pop("state")
            if expected != actual:
                raise SandboxError("Hosted computer identity changed")
        if running and (current is None or current.state != "running"):
            raise SandboxError("Hosted computer is not running")
        return current

    async def _control(self, handle: SandboxHandle, operation: str, payload: Mapping[str, Any]) -> Dict[str, Any]:
        await self._owned(handle, running=True)
        body = json.dumps(dict(payload), allow_nan=False).encode()
        if len(body) > 1024 * 1024:
            raise ValueError("Hosted control request exceeds 1 MiB")
        argv = ["python", "-I", "-m", "agno.sandbox.hosted_runtime", operation]
        if operation != "init":
            name = uuid4().hex + ".json"
            await _drain(self._write(handle.provider_ref, "/var/lib/agno-control/" + name, body))
            argv.append(name)
        result = await _drain(self._command(handle.provider_ref, argv, timeout=float(payload.get("timeout", 120)) + 15))
        if result.exit_code or result.timed_out or result.output_limited:
            raise SandboxError("Hosted control operation failed: " + result.stderr[-1000:])
        if len(result.stdout.encode()) > 4 * 1024 * 1024:
            raise SandboxError("Hosted control reply exceeds 4 MiB")
        value = json.loads(result.stdout)
        if not isinstance(value, dict):
            raise SandboxError("Hosted control reply must be an object")
        return value

    async def arpc(self, handle: SandboxHandle, operation: str, payload: bytes) -> ExecResult:
        if operation not in ("start", "poll") or not isinstance(payload, bytes) or len(payload) > 1024 * 1024:
            raise ValueError("Runtime RPC requires start/poll and a payload no larger than 1 MiB")
        # Lost control replies do not stop or repeat the native execution.
        value = await self._control(handle, operation, json.loads(payload))
        return ExecResult(0, json.dumps(value), "")

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
        if (
            not math.isfinite(timeout)
            or timeout <= 0
            or type(max_output_bytes) is not int
            or not 1 <= max_output_bytes <= 1024 * 1024
        ):
            raise ValueError("Hosted timeout must be positive and output limit between 1 byte and 1 MiB")
        if not isinstance(stdin, bytes) or len(stdin) > 512 * 1024:
            raise ValueError("Hosted command input must be bytes no larger than 512 KiB")
        await self._owned(handle, running=True)
        try:
            value = await self._control(
                handle,
                "exec",
                dict(
                    argv=list(argv),
                    timeout=timeout,
                    max_output_bytes=max_output_bytes,
                    stdin=base64.b64encode(stdin).decode(),
                ),
            )
            result = ExecResult(**value)
            if result.timed_out or result.output_limited:
                await _drain(self.astop(handle))
            return result
        except BaseException:
            await _drain(self.astop(handle))
            raise

    async def astop(self, handle: SandboxHandle) -> None:
        # The initial hosted contract uses cold replacement; stop is permanent.
        await self.adestroy(handle)

    async def adestroy(self, handle: SandboxHandle) -> None:
        row = await self.journal.ainspect(self.namespace, handle.name)
        if row is None or row["provider_ref"] != handle.provider_ref or row["digest"] != handle.config_digest:
            raise SandboxAllocationUnknown("Refusing to delete an unowned allocation")
        current = await self._owned(handle) if row["state"] != "retired" else None
        if current is not None:
            await _drain(self._delete(handle.provider_ref))
            remaining = await _drain(self._get(handle.provider_ref))
            if remaining is not None and remaining.state not in ("exited", "dead"):
                raise SandboxError("Provider did not confirm compute termination")
        await self.journal._retire(self.namespace, handle.name, row["token"], handle.provider_ref)

    @abstractmethod
    async def _create(self, spec: SandboxSpec, metadata: Dict[str, str]) -> HostedComputer: ...

    async def _check_resources(self, spec: SandboxSpec, computer: HostedComputer) -> None:
        """Adapters with fixed template resources verify them after durable binding."""

    @abstractmethod
    async def _get(self, provider_ref: str) -> Optional[HostedComputer]: ...

    @abstractmethod
    async def _inventory(self, token: str) -> Sequence[HostedComputer]: ...

    @abstractmethod
    async def _delete(self, provider_ref: str) -> None: ...

    @abstractmethod
    async def _command(self, provider_ref: str, argv: Sequence[str], *, timeout: float) -> ExecResult: ...

    @abstractmethod
    async def _write(self, provider_ref: str, path: str, payload: bytes) -> None: ...

    @abstractmethod
    async def _read(self, provider_ref: str, path: str, *, max_bytes: int) -> bytes: ...
