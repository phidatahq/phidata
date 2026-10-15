"""Company work with reusable agents, durable execution and recurring Tasks.

Set ENABLE_MANAGER=true only with the AgentOS Manager feature installed.
Set SANDBOX_IMAGE and SANDBOX_CHECKPOINTS to enable Product Engineer.
Use an image with the sandbox repository workspace runtime installed.
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
image = environ.get("SANDBOX_IMAGE")
if image:
    from agno.agents.codex import CodexAgent
    from agno.sandbox.checkpoint import FileCheckpointStore
    from agno.sandbox.docker import DockerSandbox

    engineer = CodexAgent(
        id="product-engineer",
        name="Product Engineer",
        db=db,
        sandbox=DockerSandbox(
            image=image,
            network="isolated",
            workspace_mb=1024,
            checkpoints=FileCheckpointStore(environ["SANDBOX_CHECKPOINTS"]),
        ),
        sandbox_mode="workspace-write",
        approval_mode="deny_all",
        instructions="Implement the accepted Task in the prepared repository. Start the application in isolation, run its checks, and report the diff, actual results and failures. Do not merge or deploy.",
        output_schema=WorkResult,
    )
    agents.append(engineer)

options = {}
if environ.get("ENABLE_MANAGER", "false").lower() == "true":
    from agno.os import OSManager

    options["manager"] = OSManager(
        model=model,
        root=environ.get("PLATFORM_ROOT"),
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
