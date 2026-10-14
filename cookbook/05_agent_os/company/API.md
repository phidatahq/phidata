# Company API

Company mounts `/company/v1` only with `AgentOS(company=CompanyConfig(db=...))`.
It uses AgentOS authentication and authorization. PostgreSQL is required for
Company; apply the explicit migration command before serving a new schema version.

## Records

All records have immutable `id`, readable `key`, optimistic `version`, timestamps
and `permitted_actions`. Names are not keys. Every record has one `instructions`
field. Products carry `name`; Projects and Tasks carry `title`.

| Record | Other important fields |
| --- | --- |
| Product | `owner_id`, `agent_id`, `state`, `counts` |
| Project | `product_id`, `owner_id`, `state`, derived `status`, `counts`, `summary`, `summary_at`, `summary_sources` |
| Task | `product_id`, nullable `project_id`, nullable `status`, `accountable_owner_id`, optional `assignee_id` and `agent_id`, `state`, `evidence`, `schedule`, `schedule_id` |

`state` is active or archived. Project status is derived as empty, active or
completed. Task status is null for direct work; Project Tasks use backlog, ready,
in_progress, in_review or done. Product and Project counts exclude archived Tasks.
Completion requires a nonempty Project with every unarchived Task Done.

## HTTP surface

- Products: list/create/get/patch, archive/restore, members.
- Projects: list/create/get/patch, archive/restore, comments, generated summary.
- Tasks: list/create/get/patch, archive/restore, comments, transitions, runs, schedule.
- `/me` and `/activity`: caller capabilities and permission-filtered activity.

Project creation is `POST /products/{id}/projects`. Task creation is
`POST /products/{id}/tasks` with optional `project_id`. Project transitions were
removed; progress is derived. Task transition bodies use `to_status`, optional
`reason`, `evidence` and `acceptance_check`.

Lists use bounded `limit` (default 50, maximum 100) and an opaque query-bound
`cursor`. Supported filters include Product, Project, Task stage, archive state,
owner/assignee, key and direct work. Authorization precedes pagination and counts.
`GET /tasks/{id}?project_id=...` validates the contextual parent.

Mutations require `Idempotency-Key`. Changes to existing records require a quoted
positive `If-Match` version. Responses return `ETag`, `X-Request-ID` and no-store.
A 412 means reload and reconcile; a 409 can mean an invalid transition, active run,
archived parent or conflicting reuse of an idempotency key. Errors carry a code,
message and request ID. No hard-delete operation is exposed.

## Execution and recurrence

`POST /tasks/{id}/runs` accepts `{}` or `{"message":"Revision direction"}` and
returns 202 with stable `run_id`, `session_id`, status and `result_url`. A durable
queue must be running. Project work must be Ready or In progress; direct work has
no board transition. Tasks and their Products/Projects must be active.

`GET /tasks/{id}/runs` returns the latest 100 attempts, including skipped scheduled
occurrences. `GET /tasks/{id}/runs/{run_id}` reads the linked runtime result.
`POST /tasks/{id}/runs/{run_id}/cancel` requests cancellation through the existing
queue; cancellation does not mark business work Done. This cancellation action is
idempotent and does not require a record version.

Run statuses are dispatch_pending, queued, running, paused, completed, failed,
cancelled, skipped or unavailable. They are separate from Task stages. Native
AgentOS run/session APIs remain available for conversation and HITL continuation.
The run association stores references and dispatch identity, not a second transcript.

`PUT /tasks/{id}/schedule` accepts a five-field `cron`, IANA `timezone` and `enabled`
(default true). Only the schedule owner can change its saved authority. It uses the
existing AgentOS Schedule record, poller and executor. Company checks the Task's
saved configuration and owner before dispatch, then tracks actual completion.
Only direct Tasks recur. Pause before grouping. Overlap is skipped rather than
queued; recovery preserves overdue schedule time and executes one coalesced tick.

Configure a registered Agent or CodexAgent with persistent runtime storage. Product
default agents and Task overrides must be authorized for the configuring caller.
Platform specialists are not eligible Company workers. Codex needs an explicit
existing workspace; workspace allocation and containment are deployment concerns.

## Identity and review

Product membership is mandatory in addition to provider permissions. Readers read;
contributors create/update work and perform work transitions; owners manage the
Product and review accepted work. Company uses `company:manage` and per-Product
`company_products:{read,write,review,manage}` scopes with the existing provider.
Worker dispatch additionally checks `agents:{id}:run` or the provider's equivalent.
Company access grants no platform or builder access.

HTTP principals come from verified AgentOS context. CompanyTools inherits that
context through inline and queued Team delegation. It rechecks current membership,
the active human and provider policy; prompts and model arguments cannot select a
principal. Worker actions record the executing agent separately from the initiating
human. Scheduled work preserves an explicit authorization grant, not a bearer token;
disable the owner or revoke Product membership to stop new dispatches.

Agents can create/edit drafts, group draft Tasks, comment, refresh generated summaries
and run preconfigured work. They cannot create Products, change ownership, schedules
or workers, accept Ready/Done, or replace accepted instructions. Summary writes carry
the versions of all unarchived Project Tasks; stale source sets fail with 412.

## Migration and recovery

Version 3 combines prior purpose/outcome/description and acceptance text into
instructions, retains legacy lifecycle values, maps cancellation to archive and
removes board stages from direct work. IDs, comments and activity survive.
The current initializer includes run associations and schedule references. No migration runs on startup.
Back up Company and runtime databases before deployment. Restore both for run history.

Separate Company and runtime databases are supported without a distributed
transaction. A committed intent plus stable runtime ID recovers queue submission;
startup and history reads reconcile completed attempts. Default execution makes one
queue attempt; interrupted external work is visible rather than silently rerun.

The current examples are a bounded pilot. Live provider quality, multi-replica
operation and automatic workspace provisioning require separate deployment validation.


Cancellation covers queued and executing work. Cancellation before queue acceptance
is durable and prevents startup recovery or a request retry from dispatching that run.
While an executing worker stops, its status may remain running; poll until terminal.
Cancelling a run does not mark its Project Task Done. Apply the current initializer before
starting this version; it preserves previous records and adds cancellation intent.
