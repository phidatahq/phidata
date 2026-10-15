# Company Products

Manage standing responsibilities with SQLite for development.
PostgreSQL is supported for production, with the same sync and async methods.

| File | What it teaches |
| --- | --- |
| `01_manage_products.py` | Create two owners' Products, list unscoped or by owner, soft-delete, inspect and restore. |

Run with the development environment:

```bash
.venv/bin/python cookbook/05_agent_os/30_company/01_manage_products.py
```

For HTTP access, configure `AgentOS(db=db, company=CompanyConfig())` using
`AgentOS` and `CompanyConfig` from `agno.os`. An explicit `CompanyConfig(db=...)`
overrides the OS database. Omitting Company leaves its routes and scopes absent.

The routes are `GET` and `POST /company/products`, `GET`, `PATCH` and
`DELETE /company/products/{id}`, and `POST /company/products/{id}/restore`.
Lists return `{data, meta}` with `limit` and `page`; reads accept
`include_deleted=true`. Restore requires `products:delete`, like deletion.
Read and create/update require `products:read` and `products:write` respectively.

`CompanyManager` takes a sync database; `AsyncCompanyManager` takes an async
database and exposes the same methods as coroutines. `list()` returns rows and
a total. `user_id=None` is unscoped; a string filters by owner before paging.
The HTTP layer derives ownership from authenticated identity. Reads are
company-wide for callers with the read scope. With isolation on, writes to
another owner's Product return 403. Unscoped callers with the write scope can
change every Product; admins bypass owner isolation.

## Work records

| File | Demonstrates |
| --- | --- |
| `02_manage_projects.py` | Product-contained Projects, owner filtering, explicit transitions, soft delete and restore. |
| `03_manage_tasks.py` | Backlog proposals, executor acceptance, frozen scope, rescoping, review and completion. |

Projects start `proposed` and move to `active`, then `done`. Tasks start
`backlog` and move through `ready`, `in_progress`, `in_review`, and `done`.
Either can be `cancelled` from any non-terminal state. Each transition takes
`target` and a non-empty `reason`; history is returned on the record. Tasks
may return to Backlog to clear acceptance and change scope, and In review may
return to In progress for revisions. Terminal states cannot transition.

The HTTP routes use `/company/projects` and `/company/tasks`, with the same
CRUD, paging, soft delete and restore conventions as Products, plus
`POST /{id}/transitions`. Task Ready requests include `executor_type` and
`executor_id`; the API applies the scheduler's caller run-permission check.
Acceptance also validates the executor against the registry. Direct Python callers
pass `registry=Registry(...)` to their Company manager.

Project and Task HTTP reads are company-wide for callers with the resource's
read scope, matching Products. Edits and transitions are collaborative: callers with the resource write
scope can update or transition another creator's work, even with user isolation
enabled. This includes cancellation and returning Tasks to Backlog. The creator
stays unchanged, and transition history records the acting caller. Ready still
requires the caller's executor run permission; accepted Tasks must return to
Backlog before editing. Delete and restore remain owner-scoped when user
isolation is enabled, with the existing admin bypass.
New work can use another owner's Product or Project, with the Task and
Project still required to belong to the same Product. Manager and storage
methods retain explicit owner filters for direct callers.


## Playbook and Product Manager

| File | Demonstrates |
| --- | --- |
| `04_manage_playbook.py` | Sync/async wiki namespaces, atomic page creation, version conflicts and the learning decision log without a model. |
| `05_product_manager.py` | Model resolution, a standalone Product Manager, bounded Company tools and explicit MCP publication without a model call. |

Each Product has a durable wiki namespace with `brief.md` (human direction) and
`status.md` (current work). A second namespace holds company context. Default
pages are created on first access and never reset. GET `/company/products/{id}/wiki`
lists pages; GET and PUT `/company/products/{id}/wiki/{path}` read and write them.
The company namespace has the same surface at `/company/wiki`. Writes require the
filesystem `expected_version` read with the page; zero means create only. Conflicts
return 409. Pages are Markdown and paths must be relative and normalized.

Wiki reads require `wiki:read`; writes require `wiki:write`. Product ownership
controls writes under isolation. Company pages are unowned shared documents, so
only unscoped callers (admins, or isolation disabled) can change them. Every caller
with read permission can read both namespaces. Company services use FileSystem;
its existing backend owns storage and version checks.

GET and POST `/company/decisions` use `decisions:read` and `decisions:write`.
Decisions are learning log entries in the `company` namespace, never a file.
Listings support text, agent, session and age filters plus standard paging.
The server stamps human identity; agents get identity from injected run context.
Automatic learning recall includes human and agent decisions across the company;
explicit searches can still filter by agent. The learning machine binds the agent
ID when supplying decision tools. Standalone CompanyTools and direct MCP calls
leave agent attribution unset. The log is append-only: later outcomes are new
entries that reference the original decision.

Product Manager uses `CompanyConfig(model=...)`, otherwise the first declared
registry model. If neither exists, its unavailable reason appears in diagnostics
and manual APIs still work. With OS Manager enabled it is an internal member;
otherwise it is a standalone agent, available at `GET /agents/product-manager-internal`
and `POST /agents/product-manager-internal/runs`. Its id is reserved and its tools stay out of
the registry. It proposes Projects and Backlog Tasks, edits owned proposals,
updates `status.md` with a version check, and logs decisions through its learning
machine. It has no acceptance, completion, owner, Sources or scheduler tools.

CompanyTools can be published explicitly with `MCPConfig(tools=[...])`, following
the existing MCP toolkit convention. Direct MCP calls have the same write fence.
The examples make no provider calls; they do not demonstrate live model quality.
Routines and Sources are outside this delivery.

Optional Company tool arguments accept `null` for omission. Empty strings are
normalized to omission as well; omitted pagination uses 20 results on page 1.
Required identifiers and titles still require valid values.

Async PostgreSQL derives its default database ID from the connection URL and
schema, like synchronous PostgreSQL. Async SQLite already derives a stable ID
from its connection details. Reuse those details (or an explicit stable `id`)
after restart and across replicas so saved run database references resolve.
This does not rewrite references saved with older randomly generated IDs;
retaining a known old ID explicitly is necessary for those references.



## Execution and attention

`06_execute_tasks.py` starts an accepted workflow Task through its ordinary run
route and the durable queue, waits for In review, reads paged history and checks
attention. It makes no provider calls. Start PostgreSQL with
`./cookbook/scripts/run_pgvector.sh`, then run:

```bash
.venv/bin/python cookbook/05_agent_os/30_company/06_execute_tasks.py
COMPANY_DB=postgres .venv/bin/python cookbook/05_agent_os/30_company/06_execute_tasks.py
```

The default stores Company records and sessions in temporary SQLite, with a
PostgreSQL queue. `COMPANY_DB=postgres` uses PostgreSQL for both. The example
creates and removes its own database schema. `COMPANY_QUEUE_DB_URL` overrides
the local PostgreSQL URL. SQLite follows the queue's existing development
fallback; use PostgreSQL session storage for production attempt fencing.

POST `/company/tasks/{id}/runs` accepts `{"attempt": 1}` (the default). Repeating
that attempt returns the first run. A new attempt increments the number; after
success, first transition In review to In progress to request revisions. Each
Task retains one session. GET on the same route returns ordinary session runs
with `limit` and `page`. GET `/company/runs/{id}` reads an individual run and
POST `/company/runs/{id}/cancel` uses the executor's existing cancellation route.

Start rechecks the registry, `tasks:write`, `wiki:read` and the executor's run
permission. Registry-only executors receive their ordinary routes when Company
is enabled. Each executor needs a run database, and execution requires
`QueueConfig(durable=True)`. An existing session retains the normal run route's
ownership checks. Engineering executors cannot be started yet.

Executor input contains only the Task brief, its evidence and the current
company and Product wiki pages. Queue retries and restart recovery use the
existing queue policy. Results are saved on the Task; success moves it to
`in_review`. Failure leaves the Task visible with an error result. Executors
cannot acquire scheduler mutation authority.

GET `/company/attention?product_id=...` returns `proposals`, `in_review` and
`failed` counts using the Task list filters. Omitting Product counts all work.
Attention and run reads are company-wide with `tasks:read`; Task lists also
accept `failed=true`. Existing databases add the Task execution columns with
`MigrationManager(db).up(table_type="tasks")` (await this migration coroutine).
