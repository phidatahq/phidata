"""Company work with reusable agents, durable execution and recurring Tasks.

Set ENABLE_MANAGER=true only with the AgentOS Manager feature installed.
Set CODING_WORKSPACE to a dedicated disposable worktree to enable the coding pilot.
The scheduler automatically picks up accepted Ready Tasks and due recurring Tasks.
Set GITHUB_TOKEN for read-only verification of private reviewer-linked PRs.
"""

from os import environ

from agno.db.postgres import PostgresDb
from agno.models.openai import OpenAIResponses
from agno.os import AgentOS, Authorization, CompanyConfig, QueueConfig, UserDirectory
from pydantic import BaseModel


class WorkResult(BaseModel):
    summary: str
    checks: list[str]
    needs_review: bool


db = PostgresDb(db_url=environ["COMPANY_DATABASE_URL"])
model = OpenAIResponses(id="gpt-5.6-luna")
agents = []
workspace = environ.get("CODING_WORKSPACE")
if workspace:
    from agno.agents.codex import CodexAgent

    coder = CodexAgent(
        id="coding-agent",
        name="Coding Agent",
        db=db,
        cwd=workspace,
        sandbox="workspace-write",
        approval_mode="deny_all",
        instructions="Work only on the requested Task. Run its checks and report the diff. Do not merge or deploy.",
        output_schema=WorkResult,
    )
    agents.append(coder)

options = {}
if environ.get("ENABLE_MANAGER", "false").lower() == "true":
    from agno.os import ManagerConfig

    options["manager"] = ManagerConfig(
        model=model,
        workspace=environ.get("PLATFORM_WORKSPACE"),
        instructions="Delegate Company work to Product Manager. Platform specialists manage the AgentOS runtime.",
    )

agent_os = AgentOS(
    id=environ.get("AGENT_OS_ID", "company"),
    db=db,
    agents=agents,
    company=CompanyConfig(db=db, model=model, github_token=environ.get("GITHUB_TOKEN")),
    authorization=Authorization(
        verification_keys=[environ["JWT_VERIFY_KEY"]],
        algorithm=environ.get("JWT_ALGORITHM", "RS256"),
        audience=environ.get("AGENT_OS_ID", "company"),
    ),
    user_directory=UserDirectory(db=db, auto_provision=False),
    queue=QueueConfig(durable=True, max_concurrency=1),
    scheduler=True,
    **options,
)
app = agent_os.get_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=7777)
