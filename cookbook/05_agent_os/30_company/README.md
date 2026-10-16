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
machine. It can read Sources and add website Sources with permission and Product
ownership. Acceptance, completion, ownership changes, local Source additions and
scheduling remain outside its tools.

CompanyTools can be published explicitly with `MCPConfig(tools=[...])`, following
the existing MCP toolkit convention. Direct MCP calls have the same write fence.
The examples make no provider calls; they do not demonstrate live model quality.
The heartbeat examples below demonstrate Routines and Sources.

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

| File | Demonstrates |
| --- | --- |
| `06_execute_tasks.py` | Durable execution, duplicate starts, ordinary run history and attention with no model call. |

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
that attempt returns the first run. A full queue returns 429 without changing
the Task or consuming the attempt; retry the same attempt when capacity is available.
The durable ticket is accepted before the Task moves to In progress, and the worker
can recover that update if the submitting process stops. If acceptance changes
before the Task can reserve a fresh ticket, the request returns 409 and cancels
the waiting ticket; an already-claimed ticket is rejected by the worker.
A new attempt increments the number; after
success, first transition In review to In progress to request revisions. Each
Task retains one session. GET on the same route returns ordinary session runs
with `limit` and `page`. GET `/company/runs/{id}` reads an individual run and
POST `/company/runs/{id}/cancel` uses the executor's existing cancellation route.

Start rechecks the registry, `tasks:write`, `wiki:read` and the executor's run
permission. Registry-only executors receive their ordinary routes when Company
is enabled. Each executor needs a run database, and execution requires
`QueueConfig(durable=True)`. An existing session retains the normal run route's
ownership checks. Engineering executors cannot be started yet. Framework-reserved executors,
including Product Manager and OS Manager, cannot be accepted or started as
Task executors.

Executor input contains only the Task brief, its evidence and the current
company and Product wiki pages. Queue retries and restart recovery use the
existing queue policy. Results are saved on the Task; success moves it to
`in_review`. Retryable failures remain outside failed attention while the queue
has attempts left. An exhausted, permanent or cancelled run leaves the Task
In progress with a visible `ERROR` or `CANCELLED` result. It can start another numbered attempt or return to
Backlog for replanning. Executors cannot acquire scheduler mutation authority.

GET `/company/attention?product_id=...` returns `proposals`, `in_review` and
`failed` counts using the Task list filters. Omitting Product counts all work.
Attention and run reads are company-wide with `tasks:read`; Task lists also
accept `failed=true`. Failed work means an In progress Task whose latest result
is `ERROR` or `CANCELLED`. Moving the Task to Cancelled, Backlog, Ready or In review
clears it from failed attention while preserving the result as history. Starting
a new attempt clears the previous result. `failed=false`
includes all other Tasks, including those with no result. The Task table is
created with its execution, evidence and result columns in the initial schema.

## Cascading archive

| File | Demonstrates |
| --- | --- |
| `07_cascading_archive.py` | Active-work refusal, moving a Backlog Task, cascading archive, hidden children, and exact restore with sync and async managers. Add `--postgres` for PostgreSQL. |

Archiving a Product archives all its active Projects and Tasks. Archiving a
Project archives its active Tasks. Every cascaded child's `transitions` history
records an `action: "archive"` event with `archived_by: {type, id}` naming the
parent. Lifecycle status stays unchanged. Restore brings back only those
children; records archived separately or before the parent stay archived.
Restore the parent before restoring individual children.

A Product or Project with Ready, In progress, or In review Tasks refuses archive,
even if an active Task was separately archived.
The API returns 409 with `detail.message` and `detail.tasks`, an array of `{id,
title}` objects. Managers raise `ValueError` with the same detail dictionary.
Finish or cancel that work first. Backlog Tasks may move to another active
Project in the same Product using `PATCH /company/tasks/{id}` with `project_id`;
Product membership is immutable.

Project and Task lists always hide children of archived parents, including when
`include_deleted=true`. Totals and pagination follow the same visibility rule.
Use `include_deleted=true` on the parent's own list to find it, or read an
individual archived record with that flag. Cascades and restores run in one
database transaction; refusal leaves the entire hierarchy unchanged.

Standalone Task archive and restore change visibility without adding lifecycle
transitions, preserving acceptance for an existing queued run. Restore closes an
archive history event only when one was recorded by a cascade. Returning to
Backlog or otherwise changing acceptance still invalidates an old queue ticket.
For records archived by older versions that left live children behind, restore
the parent before editing or restoring those children; individual reads remain
available with `include_deleted=true`.

Cascade writes currently update each child inside one transaction. Large archives
hold the Product lock until all child updates finish; bulk-update optimization is
a separate follow-up. The list-page query bound is independent of archive size.

Product and Project reads also carry `counts`. A Product has `counts.projects`
(the number of proposed or active Projects) and `counts.tasks` with integer
`backlog`, `ready`, `in_progress`, `in_review`, `done`, and `cancelled` fields.
A Project has the same `counts.tasks` object. Missing statuses are zero.
Archived children and children of archived parents contribute nothing, even
when the parent's own read includes archived records. Managers and HTTP use
`BaseDb.get_product_counts(ids)` or `get_project_counts(ids)` and their async
twins, issuing one grouped query for the entire returned page. A warmed list
page uses three SQL statements in total, regardless of the number of cards.

## Heartbeat

| File | Demonstrates |
| --- | --- |
| `07_heartbeat.py` | Code-declared Products, a reader Source, an Intake Skill, scheduler rows and duplicate-free scans without a model call. |

Declare `Product`, `Source` and `Routine` from `agno.company`, then pass
`CompanyConfig(products=[...])`. The same declarations work in OS configuration:

```yaml
company:
  products:
    - id: documentation
      name: Documentation
      purpose: Keep docs current
      sources:
        - type: markdown
          reference: /workspace/docs
          credential_ref: DOCS_ACCESS_TOKEN
      routines:
        - name: intake
          template: intake
          executor_type: agent
          executor_id: source-reader
          cron_expr: "0 9 * * 1-5"
```

The executor must already be registered; an invalid declared target fails startup
instead of silently dropping its Routine. Give it `CompanyTools(db)` and
`load_routine_skills()` for reader, Intake and Summary tools. AgentOS binds its
interfaces to custom `CompanyTools(db)` executors automatically; an explicit
`interfaces=` override is preserved, and `summary_tools=False` disables delivery.
Product Manager has no outbound Summary tool. Enable the existing AgentOS scheduler and queue to run schedules; the
cookbook only creates and inspects them. Scheduling never grants acceptance.
The OS scheduler database owns Routine definitions/history even with a separate
Company database. `metadata.routine_ids` links them to Products.

The templates are packaged `SKILL.md` files under `agno/company/skills`, loaded
through `LocalSkills`. Creation snapshots the selected Skill's instructions into
the schedule, with the Product id explicitly included in the model message.
Following scheduler behavior, restarting or editing a Skill never overwrites
human-edited schedule instructions. Apply revised instructions to an existing
Routine with an authorized PATCH to `/company/routines/{id}`.
Source types are `git` (a local checkout), `markdown` (a
file or directory), and `website` (a single page). Optional `config.paths` limits
local reads to relative files. Workspace exclusions and path confinement apply;
credential references name environment variables, whose presence diagnostics
report without disclosing values. These readers use local files or an unauthenticated
website GET: `credential_ref` is a diagnostic prerequisite, not an authentication
adapter, and its value is never passed to an executor or reader.
Source reads require `sources:read`, not a separate filesystem grant.
`read_company_source` without `path` returns a content-free index (`data`,
`total_count`, `next_offset`). Use a filename glob in `pattern` and `offset`/`limit`
to page through it. Discovery does not open document contents. Pass a returned
`path` to read one document; the response contains evidence and up to 8,000
characters by default (`max_chars` can be 1..16,000). `next_content_offset` lets
you continue a large document using `content_offset`. Every tool response is
capped at 64 KiB of serialized JSON, including metadata. The full-document
`content_hash` must stay the same across fragments; reread if it changes.
Selection can narrow but never expand a human's `config.paths`, and Workspace
exclusions and root confinement still apply. Website Sources only read their
configured URL. The programmatic whole-Source `read_source` API still skips
undecodable/oversized directory entries and reports `skipped_paths`; explicit
selected-file reads fail on reader errors.
Source reads produce evidence with the run id,
a SHA-256 hash of reader content, and a link. Task deduplication is per Product,
including completed and soft-deleted proposals. Failed reads create no proposals.
Reader failures fail the executor and Routine run, appear in Routine history,
and contribute to the Product's failed attention count. Routine authority uses
the configured Source's confined reader under `sources:read`; the human creating
the Routine does not need an additional `filesystem:read` grant.
Reading files creates no Tasks. The reader first decides whether useful work is
needed, then supplies a title, concise brief, selected `evidence_links`, an
`evidence_hashes` mapping from each selected link to the `content_hash` observed
in the preceding read, and a stable Source-local `proposal_key` to Intake.
Intake rereads only the selected links, verifies their hashes, and rejects
evidence changed since observation. Read again and reconsider the proposal after
such a rejection. It stores hashes and links, without copying document content
into the Task. Reuse the issue key across content and wording edits; a distinct issue
has a distinct key. Database uniqueness remains scoped to the Product.
Routines must use evidence-backed Intake: plain `propose_company_task` and
Company service Task creation reject Routine authority. Human and Product Manager
proposals retain their normal behavior.

`/company/routines` wraps the scheduler. Writes require both `routines:write`
and `schedules:write`; histories require `routines:read` and `schedules:read`.
Routine creation saves the schedule disabled, links its id to the Product, then
activates it through the scheduler. If linking or activation fails, retrying the
same request as the same creator resumes the pending creation. Edited requests
and already-created schedules still return 409; a retry never undoes a deliberate
pause. Resume also repairs a missing Product link before activation.

Routine reads and histories are company-wide, including under user isolation.
Writes retain scheduler ownership; under user isolation, another user's mutation
returns 403.
Pause/resume use scheduler disable/enable and its filtered state response; saved
authorization claims are never returned. Routine schedule names follow scheduler
validation, including the 255-character limit on `product_id + "." + name`.
Invalid names return 422 before creation, including setup. Sources use `sources:read`,
`sources:write` and `sources:delete`, with Product ownership on writes.
`POST /company/setup` uses `products:write` to seed a blank deployment; nested
Sources and Routines also require their own write permissions. Retries and
restarts repair interrupted creation and linking, retain existing edits and do not
restore archived records. Setup returns 201 for creation and 200 for a retry.
If the deployment already has Products other than this setup identity, setup
returns 409 instead of returning another owner's Product.

Summary uses Product metadata such as
`{"summary": {"interface": "slack", "destination": "C012345"}}` and the matching
interface configured on AgentOS. The executor supplies its narrative to
`summarize_company_product`; the page includes counts, that narrative, changes
since the last delivered summary, and failed-Task details. Summary updates the versioned
`summary.md` Product wiki page before delivery. Delivery receipts and the last
delivered snapshot persist in a separate Product filesystem namespace, outside
the wiki and executor input, so report retention cannot resend a delivered run or
reset the change baseline. Existing report receipts migrate before expiry.
A repeated run does not resend after intervening successful runs;
a transport failure remains a failed run with the report retained and the previous
delivery baseline unchanged. The baseline advances with the receipt only after
transport succeeds, so the next report still includes undelivered changes. Provider
retry guarantees still apply if a process dies after sending but before recording
success. No live messages are sent by this cookbook.

Task evidence identity and deduplication are part of the initial Company schema.
Task responses expose `origin`, `routine_id` and `dedupe_key`. Human-created Tasks
have origin `human`, Product Manager proposals have `product_manager`, and Routine
proposals have `routine` with the trusted Routine id.
Automatic acceptance and automatic Task pickup are not enabled by this change.

### Refresh, completion and retention

`refresh_company_product` proposes completion for active Projects with at least
one Task and only terminal Tasks. Each proposal is a versioned page under
`project-completion/`; unchanged scans do not rewrite it. New open work withdraws
the proposal. A human accepts it through the existing Project transition route.
Refresh cannot transition a Project. Moving a Project to Done returns 409 with
the open Task names and ids until every Task is Done or Cancelled, including
Tasks that were manually archived while still open.

Products store `metadata.archive_window_days`, default 14. Refresh soft-archives
Done and Cancelled Projects and Tasks whose last update is strictly older than
that window, falling back to creation time when no update exists. The delete
transaction rechecks age and terminal state. Project retention uses the same
cascading archive as manual archive: it refuses Ready, In progress or In review
Tasks, and archives remaining children even if their own updates are newer.
Restoring the Project restores only children taken by that cascade; Tasks
independently archived by their own retention window stay archived.
Restore retains the lifecycle and starts a fresh retention window. Archived
records leave normal lists, grouped counts and execution. Read an individual
record with `include_deleted=true` for inspection; lists still hide children
of archived parents, so restore the parent first.
Refresh removes expired generated `summary.md` and completion-proposal pages
through the existing filesystem API. Human pages, `brief.md` and `status.md`
are protected. The Refresh Skill updates status.md to reflect the remaining work.

The maintenance tool requires Routine authority, Product ownership when
isolation applies, `products:read`, `projects:read`, `projects:delete`,
`tasks:read`, `tasks:delete`, `wiki:read` and `wiki:write` on the saved caller.
No scheduler-write grant is added. Product Manager does not receive maintenance
or outbound Summary tools. Existing schedule instructions retain the scheduler's
snapshot behavior; apply the revised Refresh Skill through an authorized PATCH.

Products, Projects and Tasks list routes accept `sort_by=updated_at` and
`sort_order=asc|desc`. Activity ordering uses creation time for records without
an update and a deterministic id tie-breaker, before pagination. Omitting these
parameters preserves the existing creation-time descending order.

Optional Company tool arguments accept `null` for omission. Empty strings are
normalized to omission as well; omitted pagination uses 20 results on page 1.
Required identifiers and titles still require valid values.

Async PostgreSQL derives its default database ID from the connection URL and
schema, like synchronous PostgreSQL. Async SQLite already derives a stable ID
from its connection details. Reuse those details (or an explicit stable `id`)
after restart and across replicas so saved run database references resolve.
This does not rewrite references saved with older randomly generated IDs;
retaining a known old ID explicitly is necessary for those references.


### Custom Routines and discovered websites

Run `08_custom_routines.py` to create a Routine with instructions and no template
or initial Sources, then add an attributed website through `CompanyTools`.
The example is offline; the integration tests execute custom and search-style
Routines through the scheduler and durable queue on all four SQL adapters.

`template` is optional. Without one, creation requires nonempty `instructions`.
With a template, creation copies its Skill text unless explicit instructions are
supplied. Name, instructions, executor type/id, cron expression and timezone can
be edited with PATCH. Executor edits reuse scheduler authorization and target
checks. Stored instructions are not refreshed when Skill files change.
A custom Routine does maintenance only when it calls the Refresh tool, and
Summary bookkeeping only when it calls the Summary tool.

Product Manager and executors can call `add_company_source` with `type="website"`
when granted `sources:write` and permitted to write the Product. Repository and
path Sources remain human-added. Source storage has a single existing JSON
field, `config`: server-stamped `config.metadata.agent_id` and
`config.metadata.run_id` identify the first discovery. These fields are not
reader options or model-supplied identities. Matching additions reuse the same
Source; conflicting settings or archived references are refused with the existing
Source id. A human can inspect provenance in GET `/company/sources` and archive
through DELETE `/company/sources/{id}`. AgentOS applies its isolation setting to
custom Company toolkits. Non-admin scoped tokens missing a subject are rejected
under isolation on Company reads as well as writes; the existing administrator
exemption is unchanged.

Summary's unresolved failures match attention: only Tasks still `in_progress`
with an ERROR or CANCELLED execution result appear under Failed Tasks. Moving
work on or archiving it removes that unresolved failure without deleting its
execution history.
