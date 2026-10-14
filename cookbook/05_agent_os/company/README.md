# Company

Run company work on AgentOS with three concepts:

- **Product:** an ongoing responsibility, such as Framework, Documentation or Legal Operations.
- **Task:** saved work in a Product, with instructions and results.
- **Project:** an optional group of Tasks with a shared outcome.

Project Tasks move through Backlog, Ready, In progress, In review and Done.
Direct Product Tasks have no board stage. Run them when needed or give them a schedule.
Archive abandoned work. Project progress comes from its unarchived Tasks; an empty
Project is empty, and adding unfinished work makes a completed Project active again.

## Enable Company

```python
from agno.db.postgres import PostgresDb
from agno.os import AgentOS, CompanyConfig

db = PostgresDb(db_url=database_url)
agent_os = AgentOS(
    authorization=authorization,
    company=CompanyConfig(db=db),
)
app = agent_os.get_app()
```

Products, Projects and Tasks are dynamic API records. Omit `company` to leave the
capability disabled, including its routes, descriptor and background work. Manual
Company records need no model, manager or runtime database. The explicit Company
database may differ from AgentOS's runtime database.

## Add reusable workers

```python
from agno.agent import Agent
from agno.os import QueueConfig
from agno.tools.company import CompanyTools

product_manager = Agent(
    id="product-manager",
    name="Product Manager",
    model=model,
    db=db,
    tools=[CompanyTools()],
)
agent_os = AgentOS(
    db=db,
    agents=[product_manager],
    authorization=authorization,
    company=CompanyConfig(db=db),
    queue=QueueConfig(durable=True),
    scheduler=True,
)
```

The same Product Manager can manage every Product the caller may access. Creating a
Product creates no agent. Choose a Product's default `agent_id`; a Task can override
it. Execution requires permission to run that agent as well as Product membership.

With the AgentOS Manager feature installed, configure its normal `manager=` option
and add this ordinary agent to `agent_os.manager.members`. It sits beside Platform
Manager, Platform Builder and, when configured, Platform Engineer. Product Manager
gets CompanyTools, without platform toolkits. This composition is exercised by the
manager compatibility test; it does not require changes to the manager implementation.

CompanyTools receives verified identity inside AgentOS, including Team delegation
and durable queue execution. It can read work, create drafts, group draft Tasks,
comment, refresh summaries and dispatch configured work. It cannot accept work,
create Products, change membership or select new execution authority. Standalone
Python tool calls without trusted execution context fail closed.

## Minimal API journey

| Action | Endpoint under `/company/v1` | Body |
| --- | --- | --- |
| Create a Product | `POST /products` | `{"name":"Documentation","agent_id":"product-manager"}` |
| Add a direct Task | `POST /products/{id}/tasks` | `{"title":"Refresh project summaries","instructions":"Read current Tasks and refresh each generated summary."}` |
| Run it | `POST /tasks/{id}/runs` | `{}` |
| Make it recurring | `PUT /tasks/{id}/schedule` | `{"cron":"0 9 * * 1-5","timezone":"Europe/London"}` |
| Pause recurrence | Same schedule endpoint | Same timing plus `"enabled":false` |
| Create a Project | `POST /products/{id}/projects` | `{"title":"Improve onboarding","instructions":"Make the setup guide work on a clean machine."}` |
| Group a draft Task | `PATCH /tasks/{id}` | `{"project_id":"<project-id>"}` |

Clients supply their existing login, `Idempotency-Key` for mutations and `If-Match`
for versioned changes. Owners are inherited. A name/title is enough to capture work;
instructions are required before execution or accepting a Project Task into Ready.
Pause recurrence before grouping a Task. Identity, comments and run history survive.

Running is explicit. A successful Project Task run moves it to In review. A human
can request revision, which reuses the working session, or accept it as Done with
evidence or an explanation of the checks. Recurring occurrences use fresh sessions
with the previous result. One active run per Task is allowed; overlapping scheduled
occurrences are recorded as skipped. The scheduler coalesces missed intervals.

Task history links to stored AgentOS output. A queue acknowledgement is not a
completed result. Dispatch intents and stable run IDs let retries and startup
recovery reconcile partial database writes without another execution.

## Run the examples

Use a dedicated PostgreSQL development database:

```sh
source .venv/bin/activate
export PYTHONPATH="$PWD/libs/agno"
export COMPANY_DATABASE_URL='<your PostgreSQL connection URL>'
python -c 'import agno; print(agno.__file__)'
python -m agno.os.company.migrations
```

The initializer creates the current schema directly (version 5). Re-running it
leaves an existing version-5 pilot database intact. Older prototype schemas are
rejected without changes: migrate them with the tooling from their original
revision, or use a fresh development database. Never reset a database containing
work you need to keep.

Configure `JWT_VERIFY_KEY`, `JWT_ALGORITHM` and `AGENT_OS_ID` for your identity
provider. Provision known humans through UserDirectory. Clients use their normal
login; they do not construct Company identities.

- `app.py`: model-free server for manual work.
- `manual.py`: repeatable local operator exercise for human review.
- `with_agents.py`: Product Manager, durable queue and scheduler; optional OS Manager
  and Codex worker. Set `PLATFORM_WORKSPACE` to the source directory for Platform
  Engineer. Starting it makes no model calls. Dispatching work does.

For the coding pilot, set `CODING_WORKSPACE` to a dedicated disposable Git worktree
and assign `coding-agent` to one Project Task. The example serializes execution.
Company currently uses the worker's configured workspace; it does not provision
or sandbox workspaces per Task. Use a dedicated worker/worktree for this pilot.
No merge or deployment is automated.

Frontend implementation belongs in the Agno OS repository. See [API.md](API.md)
for integration details and [TEST_LOG.md](TEST_LOG.md) for executed checks and limits.
