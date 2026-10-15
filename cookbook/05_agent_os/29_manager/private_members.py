"""Expose a team while keeping an application-owned member internal.

Run the local checks without a model call:
    .venv/bin/python cookbook/05_agent_os/29_manager/private_members.py

To chat with the team, serve create_os(...).get_app() with your usual AgentOS
setup. That path requires an OpenAI API key and makes model calls.
"""

from tempfile import TemporaryDirectory

from agno.agent import Agent
from agno.db.sqlite import SqliteDb
from agno.models.openai import OpenAIResponses
from agno.os import AgentOS
from agno.registry import ComponentPolicy, Registry
from agno.team import Team
from fastapi.testclient import TestClient


def create_os(db: SqliteDb) -> AgentOS:
    registry = Registry(
        component_policies=[ComponentPolicy("agent", "researcher", public=False)]
    )
    researcher = Agent(
        id="researcher",
        name="Researcher",
        model=OpenAIResponses(id="gpt-5.6-luna"),
        instructions="Research the question delegated by the lead and report your findings.",
        db=db,
    )
    lead = Team(
        id="research-team",
        name="Research Team",
        model=OpenAIResponses(id="gpt-5.6-luna"),
        members=[researcher],
        instructions="Delegate research to your member and explain the result.",
        db=db,
    )
    return AgentOS(
        agents=[researcher], teams=[lead], registry=registry, db=db, telemetry=False
    )


if __name__ == "__main__":
    with TemporaryDirectory() as directory:
        agent_os = create_os(SqliteDb(db_file=f"{directory}/exposure.db"))
        client = TestClient(agent_os.get_app())
        assert client.get("/agents").json() == []
        assert [team["id"] for team in client.get("/teams").json()] == ["research-team"]
        assert not client.get("/teams/research-team").json().get("members")
        assert (
            client.post(
                "/agents/researcher/runs", data={"message": "hello"}
            ).status_code
            == 404
        )
        assert (
            client.post(
                "/schedules",
                json={
                    "name": "private",
                    "cron_expr": "0 0 * * *",
                    "endpoint": "/agents/researcher/runs",
                },
            ).status_code
            == 409
        )
        print("Private component checks passed; no model calls were made.")
