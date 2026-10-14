"""Two turns of one session on an AgentCore microVM. This creates billable compute.

Deploy a runtime with agentcore_setup.py, then set AGENTCORE_RUNTIME_ARN to the
ARN it printed. The default fixture harness makes no model calls.

--harness codex forwards OPENAI_API_KEY into the sandbox. --harness claude uses
Bedrock through the runtime's execution role, so it needs model access in that
account but no API key. Both real harnesses check that turn 2 recalls a codeword
that only the conversation from turn 1 holds.

Turn 2 looks the sandbox up again with create, as a new request would: the same
session and generation name the same microVM, so the harness resumes its native
session with nothing to restore.
"""

import argparse
import os
from uuid import uuid4

from agno.sandbox.agentcore import AgentCoreSandbox
from agno.sandbox.client import SandboxRuntimeClient


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--harness", choices=("fixture", "claude", "codex"), default="fixture"
    )
    parser.add_argument(
        "--model", help="Bedrock model for claude, OpenAI model for codex"
    )
    args = parser.parse_args()

    runtime_arn = os.environ["AGENTCORE_RUNTIME_ARN"]
    if args.harness == "fixture":
        env = {"AGNO_SANDBOX_TEST_RUNTIME": "1"}
        config = {}
        turns = ["Create a file", "Continue in the same session"]
    else:
        if args.harness == "claude":
            env = {
                "CLAUDE_CODE_USE_BEDROCK": "1",
                "AWS_REGION": runtime_arn.split(":")[3],
            }
            config = {
                "model": args.model or "us.anthropic.claude-sonnet-5",
                "permission_mode": "acceptEdits",
                "allowed_tools": ["Read", "Write", "Edit", "Bash"],
            }
        else:
            # Only the selected model key enters compute. The microVM is the
            # isolation boundary, so Codex runs without its own nested sandbox.
            env = {"OPENAI_API_KEY": os.environ["OPENAI_API_KEY"]}
            config = {"sandbox": "full-access"}
            if args.model:
                config["model"] = args.model
        # The codeword is never written to a file, so only the conversation from
        # turn 1 can answer turn 2.
        turns = [
            "Remember the codeword BLUE-HERON, but do not write it to any file. "
            "Create primes.py that prints the first 10 primes, run it, and report the output.",
            "What codeword did I ask you to remember? Then add test_primes.py for primes.py, "
            "run it with python, and report the result.",
        ]

    sandbox = AgentCoreSandbox(
        runtime_arn, namespace="agentcore-example-" + uuid4().hex[:12], lifetime=1800
    )
    client = SandboxRuntimeClient(sandbox)
    identity = {"session_id": "example", "agent_id": "coder", "env": env}
    handle = sandbox.create(**identity)
    try:
        for number, prompt in enumerate(turns, start=1):
            # A later request finds the same computer by its session and generation.
            current = sandbox.create(**identity)
            assert current.provider_ref == handle.provider_ref
            execution = client.start(
                current,
                execution_id=f"turn-{number}",
                run_id=f"turn-{number}",
                sdk=args.harness,
                input=prompt,
                config=config,
                execution_timeout=600,
            )
            result = None
            for page in client.pages(execution, timeout=900):
                result = page.result
            assert result is not None and result["type"] == "execution_finished", result
            content = str(result["run"].get("content"))
            print(f"Turn {number}: {result['run']['status']}")
            print(content[:800])
        listing = sandbox.exec(handle, ["ls", "-1"]).stdout.split()
        print("Workspace after both turns:", listing)
        if args.harness != "fixture":
            assert "BLUE-HERON" in content, "Turn 2 lost the conversation"
            print("Turn 2 recalled the codeword from the same native session.")
    finally:
        sandbox.destroy(handle)
        print("Destroyed", handle.provider_ref)


if __name__ == "__main__":
    main()
