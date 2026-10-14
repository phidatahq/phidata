"""Construct a manager and run the OS diagnostics. No model calls.

Shows what the OS registers, what stays out of the build palette, and the
structured report the operator agent reads through its run_diagnostics tool.

Run:
    .venvs/demo/bin/python cookbook/05_agent_os/29_manager/manager_diagnostics.py
"""

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from agno.db.sqlite import SqliteDb
from agno.models.openai import OpenAIResponses
from agno.os import AgentOS, ManagerConfig
from agno.registry import Registry
from agno.tools.calculator import CalculatorTools


def main() -> None:
    with TemporaryDirectory() as directory:
        db = SqliteDb(db_file=str(Path(directory) / "os.db"))
        registry = Registry(
            models=[OpenAIResponses(id="gpt-5.6-luna")], tools=[CalculatorTools()]
        )
        agent_os = AgentOS(
            db=db,
            registry=registry,
            manager=ManagerConfig(
                required_env=("OPENAI_API_KEY",),
                workspace=Path(__file__).parent,
            ),
            telemetry=False,
        )

        print("Served agents:", [agent.id for agent in agent_os.agents])
        print("Served teams:", [team.id for team in agent_os.teams])
        print(
            "Registry agents (the build palette):",
            [agent.id for agent in registry.agents],
        )
        print(
            "Registry tools:",
            [getattr(tool, "name", type(tool).__name__) for tool in registry.tools],
        )

        report = agent_os.run_diagnostics()
        print("Diagnostics:", report.status)
        print(json.dumps(report.to_dict(), indent=2))


if __name__ == "__main__":
    main()
