"""Watch a sandbox namespace live: container states and what the relay writes to the event stream.

Run it next to agentos_sandbox.py while you chat from the frontend. It prints a line
whenever a container appears or changes state, and one line per event the relay writes
for any run it discovers through the relay state keys. No refreshing; it tails.

    .venv/bin/python cookbook/frameworks/sandbox/sandbox_watch.py
"""

import asyncio
import json
import os
import subprocess
import time

import redis.asyncio as aioredis

NAMESPACE = os.environ.get("SANDBOX_NAMESPACE", "agentos-sandbox")
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
LABEL = "io.agno.sandbox."


def stamp() -> str:
    return time.strftime("%H:%M:%S")


async def watch_containers() -> None:
    known = {}
    while True:
        out = subprocess.run(
            [
                "docker",
                "ps",
                "-a",
                "--filter",
                f"label={LABEL}namespace={NAMESPACE}",
                "--format",
                '{{.ID}}\t{{.Label "'
                + LABEL
                + 'session"}}\t{{.Label "'
                + LABEL
                + 'generation"}}\t{{.State}}',
            ],
            capture_output=True,
            text=True,
        ).stdout
        seen = set()
        for line in out.splitlines():
            container_id, session, generation, state = line.split("\t")
            seen.add(container_id)
            if known.get(container_id) != state:
                verb = "appeared" if container_id not in known else "is now"
                print(
                    f"{stamp()}  container  session={session} gen={generation}  {verb} {state}",
                    flush=True,
                )
                known[container_id] = state
        for container_id in list(known):
            if container_id not in seen:
                print(f"{stamp()}  container  {container_id[:12]} removed", flush=True)
                known.pop(container_id)
        await asyncio.sleep(1.0)


async def watch_events() -> None:
    from agno.os.event_streams import RedisEventStream

    store = aioredis.from_url(REDIS_URL, decode_responses=True)
    stream = RedisEventStream(aioredis.from_url(REDIS_URL))
    seen: dict = {}
    print(
        f"{stamp()}  tailing the AgentOS event stream for runs the relay follows",
        flush=True,
    )
    try:
        while True:
            for key in await store.keys("agno:os:sandbox:*:cursor"):
                _, _, _, session, run_id, _ = key.split(":", 5)
                last = seen.get(run_id, -1)
                for index, payload in await stream.replay(
                    run_id, last_event_index=last
                ):
                    seen[run_id] = max(seen.get(run_id, -1), index)
                    data = next(
                        (
                            line[5:]
                            for line in str(payload).splitlines()
                            if line.startswith("data:")
                        ),
                        None,
                    )
                    event = json.loads(data) if data else {}
                    name = event.get("event")
                    detail = ""
                    if name in ("ToolCallStarted", "ToolCallCompleted"):
                        detail = (event.get("tool") or {}).get("tool_name", "")
                    elif name == "RunContent":
                        detail = repr(str(event.get("content"))[:60])
                    print(
                        f"{stamp()}  event      session={session} run={run_id[:8]} #{index} {str(name):<18} {detail}",
                        flush=True,
                    )
                result = await store.get(key.replace(":cursor", ":result"))
                if result and seen.get(run_id + ":result") is None:
                    seen[run_id + ":result"] = True
                    run = json.loads(result).get("run") or {}
                    print(
                        f"{stamp()}  result     session={session} run={run_id[:8]} status={run.get('status')} content={str(run.get('content'))[:60]!r}",
                        flush=True,
                    )
            await asyncio.sleep(0.5)
    finally:
        await store.aclose()


async def main() -> None:
    print(f"watching namespace {NAMESPACE} and {REDIS_URL}; Ctrl-C to stop", flush=True)
    await asyncio.gather(watch_containers(), watch_events())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
