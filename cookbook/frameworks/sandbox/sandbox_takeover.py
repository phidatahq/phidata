"""Kill the AgentOS process mid-turn; a second one picks the turn up from the event stream.

What makes the relay matter: a reader that was not there when the turn started. Here that
reader is a second AgentOS process. Sequence:

1. AgentOS A serves a turn: its relay reads the container and writes to the AgentOS event
   stream in Redis; the caller's SSE stream is fed from that stream.
2. While Claude is inside a long tool call, A is killed with SIGKILL. Its relay dies with
   it. Nobody reads the container; Claude keeps working and journaling.
3. AgentOS B starts in the same namespace. Its relay finds the running execution through
   the container's health, reads the cursor A committed, and resumes from there.
4. The caller reconnects the way the frontend would, with POST /resume on B, and sees the
   whole turn: what A relayed, what B relayed, then the result. Nothing missing, nothing
   twice.

    docker run -d -p 6379:6379 redis
    ./cookbook/scripts/run_pgvector.sh
    export ANTHROPIC_API_KEY=...   # or CLAUDE_CODE_OAUTH_TOKEN
    .venv/bin/python cookbook/frameworks/sandbox/sandbox_takeover.py
"""

import json
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

import httpx
import redis

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
NAMESPACE = "takeover-" + str(int(time.time()))
SESSION = NAMESPACE  # a fresh session per run
SERVER = Path(__file__).with_name("agentos_sandbox.py")
PROMPT = "Run the bash command `sleep 12` and after it finishes reply with only the single word done."


def start_agent_os(port: int) -> subprocess.Popen:
    env = {**os.environ, "PORT": str(port), "SANDBOX_NAMESPACE": NAMESPACE}
    process = subprocess.Popen(
        [sys.executable, str(SERVER)],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(60):
        try:
            if (
                httpx.get(f"http://127.0.0.1:{port}/health", timeout=1).status_code
                == 200
            ):
                return process
        except httpx.HTTPError:
            pass
        time.sleep(0.5)
    raise SystemExit(f"AgentOS on {port} did not start")


def main() -> None:
    store = redis.from_url(REDIS_URL, decode_responses=True)
    started = time.time()

    def t() -> str:
        return f"{time.time() - started:5.1f}s"

    a = start_agent_os(7801)
    print(
        f"{t()}  AgentOS A up (pid {a.pid}), relay inside it, turns served from the event stream"
    )

    seen: list = []
    run_ids: list = []

    def caller() -> None:
        try:
            with httpx.stream(
                "POST",
                "http://127.0.0.1:7801/agents/coder/runs",
                data={"message": PROMPT, "session_id": SESSION, "stream": "true"},
                timeout=None,
            ) as response:
                for line in response.iter_lines():
                    if line.startswith("data:"):
                        try:
                            event = json.loads(line[5:])
                        except ValueError:
                            continue
                        seen.append(event.get("event"))
                        if event.get("run_id"):
                            run_ids.append(event["run_id"])
        except httpx.HTTPError:
            pass  # A is killed under this connection on purpose

    threading.Thread(target=caller, daemon=True).start()
    while "ToolCallStarted" not in seen and time.time() - started < 60:
        time.sleep(0.2)
    print(f"{t()}  caller received {seen} from A: Claude is inside `sleep 12`")

    execution_id = run_ids[0]
    cursor_key = f"agno:os:sandbox:{SESSION}:{execution_id}:cursor"
    result_key = f"agno:os:sandbox:{SESSION}:{execution_id}:result"
    os.kill(a.pid, signal.SIGKILL)
    a.wait()
    print(
        f"{t()}  killed A with SIGKILL; relay gone; cursor committed in Redis = {store.get(cursor_key)}"
    )
    time.sleep(2)
    print(f"{t()}  nobody is reading the container; Claude is still working inside it")

    b = start_agent_os(7802)
    print(f"{t()}  AgentOS B up (pid {b.pid}); its relay sweeps the namespace")

    # Read the turn the way a frontend does after losing its connection: reconnect with the last
    # index it saw, take the catch-up, and come back for more until the turn has a result.
    last_index = -1
    printed = 0
    while True:
        with httpx.stream(
            "POST",
            f"http://127.0.0.1:7802/agents/coder/runs/{execution_id}/resume",
            data={"session_id": SESSION, "last_event_index": str(last_index)},
            timeout=httpx.Timeout(10.0, read=3.0),
        ) as response:
            if printed == 0:
                print(
                    f"{t()}  POST /resume on B answered {response.status_code}; reading the indexed stream"
                )
            try:
                for line in response.iter_lines():
                    if not line.startswith("data:"):
                        continue
                    try:
                        event = json.loads(line[5:])
                    except ValueError:
                        continue
                    index = event.get("event_index")
                    if index is None or index <= last_index:
                        continue
                    last_index = index
                    name = event.get("event")
                    detail = ""
                    if name in ("ToolCallStarted", "ToolCallCompleted"):
                        detail = (event.get("tool") or {}).get("tool_name", "")
                    elif name == "RunContent":
                        detail = repr(str(event.get("content"))[:40])
                    print(f"{t()}  /resume: index {index:>3}  {str(name):<18} {detail}")
                    printed += 1
            except httpx.ReadTimeout:
                pass  # nothing new for a while; reconnect
        if store.get(result_key) is not None:
            break
        time.sleep(1.0)
    result = json.loads(store.get(result_key))
    print(
        f"{t()}  relay state: cursor {store.get(cursor_key)}, result {result['type']}, content {result['run'].get('content')!r}"
    )
    print(
        "      (A died before committing the run; in the finished stack the queue redelivers the ticket and"
    )
    print(
        "       the next worker reads the result from the event stream and commits. That piece is the coordinator.)"
    )
    os.kill(b.pid, signal.SIGTERM)
    b.wait()
    subprocess.run(
        "docker ps -a --filter label=io.agno.sandbox.namespace=%s -q | xargs -r docker rm -f >/dev/null"
        % NAMESPACE,
        shell=True,
    )


if __name__ == "__main__":
    main()
