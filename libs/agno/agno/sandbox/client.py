"""Reconnectable control-plane client for the sandbox execution journal."""

import asyncio
import json
import math
from dataclasses import dataclass
from typing import Any, AsyncIterator, Dict, Iterator, List, Mapping, Optional

from agno.sandbox.base import SandboxError, SandboxHandle, SandboxProvider, _sync


@dataclass(frozen=True)
class RuntimeExecution:
    computer: SandboxHandle
    execution_id: str
    run_id: str


@dataclass(frozen=True)
class RuntimePage:
    cursor: int
    events: List[Dict[str, Any]]
    result: Optional[Dict[str, Any]]


class SandboxRuntimeClient:
    """The provider transports requests; no DB/queue credentials enter compute.

    A lost start response is reconciled using the same execution identity and
    identical request. Polling can detach/reconnect without restarting execution.
    A runtime result is execution output, never permission to acknowledge durable
    completion. The coordinator must separately commit a recovery checkpoint.
    """

    def __init__(self, provider: SandboxProvider) -> None:
        self.provider = provider

    async def _rpc(self, computer: SandboxHandle, operation: str, request: Mapping[str, Any]) -> Dict[str, Any]:
        payload = json.dumps(dict(request), allow_nan=False).encode()
        if len(payload) > 1024 * 1024:
            raise ValueError("Runtime request exceeds 1 MiB")
        task = asyncio.create_task(self.provider.arpc(computer, operation, payload))
        try:
            output = await asyncio.shield(task)
        except asyncio.CancelledError:
            # Cancelling the caller's poll must not kill the ongoing SDK worker.
            # Drain the short RPC; explicit cancel stops the session computer.
            await task
            raise
        if output.exit_code or output.timed_out or output.output_limited:
            raise SandboxError("Runtime RPC failed: " + output.stderr[-2000:])
        try:
            response = json.loads(output.stdout)
        except ValueError as error:
            raise SandboxError("Runtime returned invalid JSON") from error
        if not isinstance(response, dict) or type(response.get("version")) is not int or response["version"] != 1:
            raise SandboxError("Runtime protocol version mismatch")
        if response.get("execution_id") != request.get("execution_id"):
            raise SandboxError("Runtime execution identity mismatch")
        return response

    async def astart(
        self,
        computer: SandboxHandle,
        *,
        execution_id: str,
        run_id: str,
        sdk: str,
        input: str,
        config: Optional[Mapping[str, Any]] = None,
        user_id: Optional[str] = None,
        execution_timeout: float = 900,
        media: Optional[List[Dict[str, Any]]] = None,
    ) -> RuntimeExecution:
        response = await self._rpc(
            computer,
            "start",
            {
                "version": 1,
                "execution_id": execution_id,
                "run_id": run_id,
                "agent_id": computer.agent_id,
                "session_id": computer.session_id,
                "sdk": sdk,
                "input": input,
                "config": dict(config or {}),
                "user_id": user_id,
                "execution_timeout": execution_timeout,
                **({"media": media} if media else {}),
            },
        )
        if response.get("accepted") is not True:
            raise SandboxError("Runtime did not acknowledge execution")
        return RuntimeExecution(computer, execution_id, run_id)

    def start(
        self,
        computer: SandboxHandle,
        *,
        execution_id: str,
        run_id: str,
        sdk: str,
        input: str,
        config: Optional[Mapping[str, Any]] = None,
        user_id: Optional[str] = None,
        execution_timeout: float = 900,
        media: Optional[List[Dict[str, Any]]] = None,
    ) -> RuntimeExecution:
        return _sync(
            self.astart(
                computer,
                execution_id=execution_id,
                run_id=run_id,
                sdk=sdk,
                input=input,
                config=config,
                user_id=user_id,
                execution_timeout=execution_timeout,
                media=media,
            )
        )

    async def apoll(self, execution: RuntimeExecution, *, cursor: int = 0) -> RuntimePage:
        if type(cursor) is not int or cursor < 0:
            raise ValueError("Runtime cursor must be a nonnegative integer")
        response = await self._rpc(
            execution.computer, "poll", {"execution_id": execution.execution_id, "cursor": cursor}
        )
        next_cursor, frames, result = response.get("cursor"), response.get("frames"), response.get("result")
        if type(next_cursor) is not int or next_cursor < cursor or not isinstance(frames, list):
            raise SandboxError("Runtime returned an invalid journal page")
        events = []
        for frame in frames:
            if not isinstance(frame, dict) or frame.get("type") != "event" or not isinstance(frame.get("event"), dict):
                raise SandboxError("Runtime returned an invalid event frame")
            event = frame["event"]
            for key, expected in (
                ("run_id", execution.run_id),
                ("session_id", execution.computer.session_id),
                ("agent_id", execution.computer.agent_id),
            ):
                if event.get(key) is not None and event[key] != expected:
                    raise SandboxError("Runtime event identity mismatch")
            if event.get("event") in ("RunCompleted", "RunError", "RunCancelled"):
                raise SandboxError("Runtime must not publish terminal service events")
            events.append(event)
        if result is not None:
            if not isinstance(result, dict) or result.get("type") not in (
                "execution_finished",
                "execution_error",
                "execution_unknown",
            ):
                raise SandboxError("Runtime returned an invalid execution result")
            if result["type"] == "execution_finished":
                run, session = result.get("run"), result.get("session")
                if not isinstance(run, dict) or not isinstance(session, dict):
                    raise SandboxError("Runtime result is missing run/session state")
                if (run.get("run_id"), run.get("session_id"), run.get("agent_id"), session.get("session_id")) != (
                    execution.run_id,
                    execution.computer.session_id,
                    execution.computer.agent_id,
                    execution.computer.session_id,
                ):
                    raise SandboxError("Runtime result identity mismatch")
        return RuntimePage(next_cursor, events, result)

    def poll(self, execution: RuntimeExecution, *, cursor: int = 0) -> RuntimePage:
        return _sync(self.apoll(execution, cursor=cursor))

    async def await_result(
        self, execution: RuntimeExecution, *, timeout: float = 900, poll_interval: float = 0.25
    ) -> Dict[str, Any]:
        """Wait without changing execution lifetime. Timeout detaches; cancel is explicit."""
        async for page in self.apages(execution, timeout=timeout, poll_interval=poll_interval):
            if page.result is not None:
                return page.result
        raise SandboxError("Runtime ended without a result")

    def wait_result(
        self, execution: RuntimeExecution, *, timeout: float = 900, poll_interval: float = 0.25
    ) -> Dict[str, Any]:
        return _sync(self.await_result(execution, timeout=timeout, poll_interval=poll_interval))

    async def apages(
        self, execution: RuntimeExecution, *, cursor: int = 0, timeout: float = 900, poll_interval: float = 0.25
    ) -> AsyncIterator[RuntimePage]:
        if not math.isfinite(timeout) or timeout <= 0 or not math.isfinite(poll_interval) or poll_interval <= 0:
            raise ValueError("Runtime polling timeouts must be positive")
        deadline = asyncio.get_running_loop().time() + timeout
        while asyncio.get_running_loop().time() < deadline:
            page = await self.apoll(execution, cursor=cursor)
            cursor = page.cursor
            yield page
            if page.result is not None:
                return
            await asyncio.sleep(min(poll_interval, max(0, deadline - asyncio.get_running_loop().time())))
        raise TimeoutError("Detached from runtime after wait timeout; execution may still be running")

    def pages(
        self, execution: RuntimeExecution, *, cursor: int = 0, timeout: float = 900, poll_interval: float = 0.25
    ) -> Iterator[RuntimePage]:
        # Reuse the tested sync poll transport; no hidden background execution.
        import time

        if not math.isfinite(timeout) or timeout <= 0 or not math.isfinite(poll_interval) or poll_interval <= 0:
            raise ValueError("Runtime polling timeouts must be positive")
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            page = self.poll(execution, cursor=cursor)
            cursor = page.cursor
            yield page
            if page.result is not None:
                return
            time.sleep(min(poll_interval, max(0, deadline - time.monotonic())))
        raise TimeoutError("Detached from runtime after wait timeout; execution may still be running")

    async def acancel(self, execution: RuntimeExecution) -> None:
        """Stop the session computer, including SDK/local tools/background children."""
        await self.provider.astop(execution.computer)

    def cancel(self, execution: RuntimeExecution) -> None:
        _sync(self.acancel(execution))
