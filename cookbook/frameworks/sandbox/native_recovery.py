"""Show what the sandbox does when the native conversation it should hold is gone.

A Claude turn continues its own native session from files under /runtime/native: Claude's
transcript and the local history database that maps the Agno session to it. After a cold
replacement those files come back from a checkpoint. This example shows the two outcomes when
they do not come back whole, in one container, by deleting the local database between turns:

- Without an expectation, the runtime cannot tell a lost database from a brand new session. The
  turn starts a fresh conversation, forgets everything, and reports COMPLETED. That is the
  behaviour before this change and the one a coordinator must never checkpoint.
- With the native id the caller committed passed as ``expected_native``, the runtime refuses
  before the model runs and reports ``native_state_missing``, so the caller retries the restore
  instead of committing a fork.

Build the image first, then export ANTHROPIC_API_KEY or CLAUDE_CODE_OAUTH_TOKEN:

    .venv/bin/python cookbook/frameworks/sandbox/build_image.py --tag agno-sandbox:local
    .venv/bin/python cookbook/frameworks/sandbox/native_recovery.py
"""

import os
import time
from uuid import uuid4

from agno.sandbox.client import SandboxRuntimeClient
from agno.sandbox.docker import DockerSandbox

credentials = {
    key: os.environ[key]
    for key in ("ANTHROPIC_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN")
    if key in os.environ
}
if not credentials:
    raise SystemExit(
        "Export ANTHROPIC_API_KEY or CLAUDE_CODE_OAUTH_TOKEN for the container"
    )

started = time.monotonic()


def say(line: str) -> None:
    print(f"[{time.monotonic() - started:5.1f}s] {line}")


config = {
    "model": "claude-sonnet-4-6",
    "permission_mode": "bypassPermissions",
    "allowed_tools": [],
    "max_turns": 2,
}
sandbox = DockerSandbox(
    image=os.environ.get("AGNO_SANDBOX_IMAGE", "agno-sandbox:local"),
    namespace="native-recovery-" + uuid4().hex,
    network="isolated",
    memory_mb=1024,
)
computer = sandbox.create(session_id="example", agent_id="coder", env=credentials)
client = SandboxRuntimeClient(sandbox)


def turn(number: int, prompt: str, expected_native=None):
    execution = client.start(
        computer,
        execution_id=f"turn-{number}",
        run_id=f"run-{number}",
        sdk="claude",
        input=prompt,
        config=config,
        expected_native=expected_native,
    )
    result = client.wait_result(execution, timeout=240)
    if result["type"] == "execution_finished":
        native = (result["session"].get("session_data") or {}).get(
            "claude_sdk_session_id"
        )
        say(
            f"turn {number}: {result['run']['status']}, answer {result['run'].get('content')!r}, native session {native}"
        )
        return native
    say(
        f"turn {number}: {result['type']}, reason {result.get('reason')}: {result['error'][:120]}"
    )
    return None


try:
    say("turn 1 starts the conversation")
    original = turn(1, "Remember the word pineapple. Reply with exactly OK.")

    say("turn 2 passes the committed native id as the expectation and continues it")
    turn(
        2,
        "What word did I ask you to remember? Reply with that word only.",
        expected_native=original,
    )

    say("now the local database is lost, as after a restore that did not land whole")
    assert (
        sandbox.exec(computer, ["rm", "-f", "/runtime/native/history.db"]).exit_code
        == 0
    )

    say("turn 3 without an expectation: the runtime sees a new session and runs anyway")
    replaced = turn(
        3,
        "What word did I ask you to remember? Reply with that word only, or NONE if you do not know.",
    )
    say(
        "that is the old outcome: a new native session "
        + str(replaced)[:8]
        + "..., no memory, reported COMPLETED"
    )

    say("turn 4 with the committed id: refused before the model runs")
    turn(
        4,
        "What word did I ask you to remember? Reply with that word only.",
        expected_native=original,
    )
    say(
        "the caller now treats this as a failed restore and retries it, instead of committing a fork"
    )
finally:
    sandbox.destroy(computer)
