"""An always-present reader that moves sandbox events into the AgentOS event stream.

The runtime inside a sandbox writes a turn's events to its journal and serves them;
something outside has to read them. The worker that started the turn can, but a worker
can be absent: restarted in a deploy, scaled away, or dead. While nobody reads, the
events wait safely in the journal, but nothing reaches Redis, so SSE, /resume and
dashboards show nothing. A relay is a reader that is always there.

It runs where the service credentials may live, outside every sandbox: inside the
AgentOS process (started by the app lifespan, one per replica) or as its own process on
the sandbox host (``python -m agno.sandbox.relay``). It lists the namespace's sandboxes
through the provider, reads each one's health for running executions, long-polls every
execution from the cursor it last committed, and hands each page to a sink. The sink
writes the events into the AgentOS event stream under the run id, the same indexed
stream SSE and /resume already read, and commits the journal cursor and the execution
result in the same transaction. A relay restart therefore resumes exactly: nothing
repeated, nothing skipped. Identity on every page comes from the provider's view of the
sandbox (the handle), never from what the journal claims.

Behaviour when parts are missing:

- A sandbox without a runtime server (no ``runtime_url``) is skipped; the owning worker
  still polls it over exec as before.
- A sandbox whose server does not answer is retried on the next sweep; the relay marks
  nothing failed. Liveness decisions belong to the coordinator.
- A sandbox whose server refuses the token is reported through ``aproblem`` and left
  alone: the relay does not guess credentials.
- A failed sink write keeps the cursor where it was, so the page is relayed again later.
  Sinks must write events and cursor atomically, or tolerate repeats.
- A relay that dies mid-page loses nothing: the journal still holds the bytes and the
  state store holds the last committed cursor.
- The relay never completes a run. Completion is the coordinator's decision after the
  checkpoint commit; the relay only makes the result available.
"""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, Set, Tuple

from agno.sandbox.base import Sandbox, SandboxError, SandboxHandle, _sync
from agno.utils.log import log_debug, log_warning


@dataclass(frozen=True)
class RelayedPage:
    """One page of events for one execution, tagged with the provider's identity."""

    session_id: str
    agent_id: Optional[str]
    generation: int
    execution_id: str
    run_id: Optional[str]
    cursor: int
    events: List[Dict[str, Any]]
    result: Optional[Dict[str, Any]]


class RelayState(Protocol):
    """What a relay must remember per execution: how far it got, and the result.

    Events do not live here; they go to the event stream. This is coordinator state and
    belongs in the session lease once the coordinator exists; until then a key-value
    store stands in.
    """

    async def aget_cursor(self, session_id: str, execution_id: str) -> int: ...

    async def aset_progress(
        self, session_id: str, execution_id: str, cursor: int, result: Optional[Dict[str, Any]]
    ) -> None: ...

    async def aget_result(self, session_id: str, execution_id: str) -> Optional[Dict[str, Any]]: ...


class MemoryRelayState:
    """Relay state in memory; for tests and single-process use."""

    def __init__(self) -> None:
        self.cursors: Dict[Tuple[str, str], int] = {}
        self.results: Dict[Tuple[str, str], Dict[str, Any]] = {}

    async def aget_cursor(self, session_id: str, execution_id: str) -> int:
        return self.cursors.get((session_id, execution_id), 0)

    async def aset_progress(
        self, session_id: str, execution_id: str, cursor: int, result: Optional[Dict[str, Any]]
    ) -> None:
        self.cursors[(session_id, execution_id)] = cursor
        if result is not None:
            self.results[(session_id, execution_id)] = result

    async def aget_result(self, session_id: str, execution_id: str) -> Optional[Dict[str, Any]]:
        return self.results.get((session_id, execution_id))


class RedisRelayState:
    """Relay state in Redis: a cursor key and a result key per execution, written together."""

    def __init__(self, url: str, *, prefix: str = "agno:os:sandbox") -> None:
        import redis.asyncio as aioredis

        self.prefix = prefix
        self._redis = aioredis.from_url(url, decode_responses=True)

    def _key(self, session_id: str, execution_id: str, part: str) -> str:
        return f"{self.prefix}:{session_id}:{execution_id}:{part}"

    async def aget_cursor(self, session_id: str, execution_id: str) -> int:
        return int(await self._redis.get(self._key(session_id, execution_id, "cursor")) or 0)

    async def aset_progress(
        self, session_id: str, execution_id: str, cursor: int, result: Optional[Dict[str, Any]]
    ) -> None:
        async with self._redis.pipeline(transaction=True) as pipe:
            pipe.set(self._key(session_id, execution_id, "cursor"), cursor)
            if result is not None:
                pipe.set(self._key(session_id, execution_id, "result"), json.dumps(result))
            await pipe.execute()

    async def aget_result(self, session_id: str, execution_id: str) -> Optional[Dict[str, Any]]:
        raw = await self._redis.get(self._key(session_id, execution_id, "result"))
        return json.loads(raw) if raw else None

    async def aclose(self) -> None:
        await self._redis.aclose()


class RelaySink(Protocol):
    """Where relayed pages go."""

    async def aget_cursor(self, session_id: str, execution_id: str) -> int: ...

    async def apublish(self, page: RelayedPage) -> None: ...

    async def aproblem(self, handle: SandboxHandle, message: str) -> None: ...


class EventStreamRelaySink:
    """Relayed events into the AgentOS event stream; cursor and result into relay state.

    Each event is added under its run id and gets the stream's own index, so a client
    reconnecting with ``last_event_index`` sees relayed events exactly as it sees a
    worker's. The run is registered as running on its first page. The sink never completes
    the run. A worker that also published the same run's events would duplicate them; for
    sandbox runs the relay is the publisher.
    """

    def __init__(self, state: RelayState, event_stream: Optional[Any] = None) -> None:
        self.state = state
        self._event_stream = event_stream
        self._registered: Set[str] = set()

    def _stream(self) -> Any:
        if self._event_stream is None:
            from agno.os.event_streams import get_event_stream

            self._event_stream = get_event_stream()
        return self._event_stream

    async def aget_cursor(self, session_id: str, execution_id: str) -> int:
        return await self.state.aget_cursor(session_id, execution_id)

    async def apublish(self, page: RelayedPage) -> None:
        from agno.run.agent import run_output_event_from_dict
        from agno.run.base import RunStatus

        stream = self._stream()
        run_id = page.run_id or page.execution_id
        if run_id not in self._registered:
            if await stream.get_run_status(run_id) is None:
                await stream.register_run(run_id, RunStatus.running)
            self._registered.add(run_id)
        for event in page.events:
            try:
                parsed = run_output_event_from_dict(event)
            except (ValueError, TypeError, KeyError):
                continue  # an event type this process does not know; the journal still has it
            await stream.add_event(run_id, parsed)
        await self.state.aset_progress(page.session_id, page.execution_id, page.cursor, page.result)

    async def aproblem(self, handle: SandboxHandle, message: str) -> None:
        log_warning(f"Sandbox relay: session {handle.session_id}: {message}")


@dataclass
class SandboxRelay:
    """Follow every execution in a provider's namespace and relay its pages to a sink."""

    provider: Sandbox
    sink: RelaySink
    sweep_interval: float = 1.0
    wait: float = 10.0
    _tasks: Dict[Tuple[str, str], asyncio.Task[None]] = field(default_factory=dict, repr=False)
    _done: Set[Tuple[str, str]] = field(default_factory=set, repr=False)

    async def asweep(self) -> List[Tuple[str, str]]:
        """One discovery pass: start following any execution not yet followed. Returns the
        (session_id, execution_id) pairs started this pass."""
        started = []
        for handle in await self.provider.alist():
            if handle.runtime_url is None or handle.state != "running":
                continue
            try:
                health = await self.provider.ahealth(handle)
            except (SandboxError, NotImplementedError) as error:
                await self.sink.aproblem(handle, str(error))
                continue
            for execution in health.get("executions", []):
                execution_id = execution.get("execution_id")
                key = (handle.session_id, str(execution_id))
                if not execution_id or key in self._tasks or key in self._done:
                    continue
                log_debug(f"Sandbox relay: following {execution_id} for session {handle.session_id}")
                self._tasks[key] = asyncio.create_task(self._follow(handle, execution))
                started.append(key)
        return started

    async def arun(self, *, stop: Optional[asyncio.Event] = None) -> None:
        """Sweep until ``stop`` is set, then cancel the followers."""
        try:
            while stop is None or not stop.is_set():
                try:
                    await self.asweep()
                except SandboxError as error:
                    log_warning(f"Sandbox relay: sweep failed: {error}")
                await asyncio.sleep(self.sweep_interval)
        finally:
            for task in self._tasks.values():
                task.cancel()
            await asyncio.gather(*self._tasks.values(), return_exceptions=True)

    def run(self, *, stop: Optional[asyncio.Event] = None) -> None:
        _sync(self.arun(stop=stop))

    async def _follow(self, handle: SandboxHandle, execution: Dict[str, Any]) -> None:
        key = (handle.session_id, str(execution["execution_id"]))
        cursor = await self.sink.aget_cursor(*key)
        try:
            while True:
                payload = json.dumps({"execution_id": key[1], "cursor": cursor, "wait": min(self.wait, 30.0)}).encode()
                try:
                    output = await self.provider.arpc(handle, "poll", payload)
                    if output.exit_code:
                        raise SandboxError(output.stderr[-500:])
                    page = json.loads(output.stdout)
                except (SandboxError, ValueError) as error:
                    # The server is briefly away, or the token was refused: say so and retry later.
                    await self.sink.aproblem(handle, f"poll {key[1]}: {error}")
                    await asyncio.sleep(1.0)
                    continue
                frames, result = page.get("frames") or [], page.get("result")
                if not frames and result is None:
                    continue
                relayed = RelayedPage(
                    session_id=handle.session_id,
                    agent_id=handle.agent_id,
                    generation=handle.generation,
                    execution_id=key[1],
                    run_id=execution.get("run_id"),
                    cursor=int(page["cursor"]),
                    events=[frame["event"] for frame in frames if isinstance(frame, dict) and "event" in frame],
                    result=result,
                )
                await self.sink.apublish(relayed)
                cursor = relayed.cursor
                if result is not None:
                    log_debug(f"Sandbox relay: {key[1]} finished; {cursor} journal bytes relayed")
                    self._done.add(key)
                    return
        finally:
            self._tasks.pop(key, None)


def main() -> None:
    """Run a relay as its own process, beside the sandboxes rather than inside AgentOS.

    SANDBOX_NAMESPACE, SANDBOX_RUNTIME_PORT, SANDBOX_RUNTIME_HOST and REDIS_URL select the
    sandboxes to follow and the Redis the AgentOS event stream and relay state live in.
    """
    import redis.asyncio as aioredis

    from agno.os.event_streams import RedisEventStream, set_event_stream
    from agno.sandbox.docker import DockerSandbox

    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    set_event_stream(RedisEventStream(aioredis.from_url(redis_url)))
    provider = DockerSandbox(
        os.environ.get("SANDBOX_IMAGE", "agno-sandbox:local"),
        namespace=os.environ.get("SANDBOX_NAMESPACE", "default"),
        network=os.environ.get("SANDBOX_NETWORK", "bridge"),
        runtime_port=int(os.environ.get("SANDBOX_RUNTIME_PORT", "8765")),
        runtime_host=os.environ.get("SANDBOX_RUNTIME_HOST", "127.0.0.1"),
    )
    relay = SandboxRelay(provider, EventStreamRelaySink(RedisRelayState(redis_url)))
    relay.run()


if __name__ == "__main__":
    main()
