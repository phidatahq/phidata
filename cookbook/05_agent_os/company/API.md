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
| Task | `product_id`, nullable `project_id`, nullable `status`, `accountable_owner_id`, optional `assignee_id` and `agent_id`, `state`, `evidence`, `schedule`, `schedule_id`, `review_pull_request`, `review_started_at`, `automation_error` |

`state` is active or archived. Project status is derived as empty, active or
completed. Task status is null for direct work; Non-recurring Tasks use backlog, ready,
in_progress, in_review or done. Product and Project counts exclude archived Tasks.
Completion requires a nonempty Project with every unarchived Task Done.

## HTTP surface

- Products: list/create/get/patch, archive/restore, members.
- Projects: list/create/get/patch, archive/restore, comments, generated summary.
- Tasks: list/create/get/patch, archive/restore, comments, transitions, runs, schedule, review PR link.
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

## Automatic progression and PR review

With `queue=QueueConfig(durable=True)` and `scheduler=True`, the existing scheduler
poller picks up newly accepted Ready Tasks with a registered worker. The run has
`trigger: "ready"`. Stable acceptance/run identity and the existing one-active-run
constraint prevent overlapping pickup. The stored Ready grant is private and does
not contain a bearer token. User activity, Product membership and agent-run permission
are checked again. Changes to accepted Task execution instructions or authority return
it to Backlog. A changed Product default does not silently substitute another worker.

`PUT /tasks/{id}/review/pull-request` accepts `url` (an exact github.com PR URL) and
`head_sha` (40 lowercase hexadecimal characters). It requires the normal mutation
headers, an eligible human Product owner with review permission, and In-review state.
The action is advertised as `link_pull_request`. Agents cannot call it through
CompanyTools. Updating the link uses the new Task version; it replaces the saved
reviewer's grant. This explicitly permits completion after any GitHub User account
merges the linked revision; no Company/GitHub account mapping is implied.

On each scheduler tick, Company checks the repository, PR number, exact head SHA,
merged state, merger account type and merge timestamp using GitHub's read-only API.
The merge must occur after this review started. Permission and Task version are
rechecked under the Product lock after the network request. A changed review or
revoked reviewer cannot be completed using stale proof. Successful verification
records `task.pull_request_merged` with actor `service:github`, the configuring
reviewer as initiating principal, and the observed merge details. A plain evidence
link cannot trigger completion. Project completion remains derived from Task states.

Set `CompanyConfig.github_token` for private PRs or authenticated API limits. It is
excluded from config repr. Requests use the fixed api.github.com origin and do not
follow redirects. Transport/provider failure leaves the Task in review with a safe
`automation_error`; a later tick retries verification. That diagnostic does not
change the accepted Task version. GitHub Enterprise and other providers are not
included. A GitHub User account can itself be automated: this gate verifies account
metadata, not a person's physical interaction. It does not merge PRs.

Explicit human Done acceptance remains available independently of GitHub. Requesting
revision clears the previous link. Failed/cancelled work stays In progress until a
deliberate retry. Ready Tasks without a worker remain manual. Turning off the scheduler
stops automatic pickup and merge checks; explicit run and acceptance remain available.

## Identity and review

Product membership is mandatory in addition to provider permissions. Readers read;
contributors create/update work and perform work transitions; owners manage the
Product and review accepted work. Company uses `company:manage` and per-Product
`company_products:{read,write,review,manage}` scopes with the existing provider.
Worker dispatch additionally checks `agents:{id}:run` or the provider's equivalent.
Company access grants no platform or builder access.

Set `CompanyConfig(db=db, model=model)` to register the framework Product Manager as
`product-manager-internal`. It uses the existing agent list/detail/run APIs and automatically
joins an enabled OS Manager Team. It is reusable across Products; membership checks
remain per caller and Product. Omit `model` to keep Company manual and model-free.
The OS Manager requires platform administration; direct Product Manager execution
requires ordinary agent-run and Company permissions.

HTTP principals come from verified AgentOS context. CompanyTools inherits that
context through inline and queued Team delegation. It rechecks current membership,
the active human and provider policy; prompts and model arguments cannot select a
principal. Worker actions record the executing agent separately from the initiating
human. Scheduled work preserves an explicit authorization grant, not a bearer token;
disable the owner or revoke Product membership to stop new dispatches.

Agents can create/edit drafts, group draft Tasks, comment, refresh generated summaries
and run preconfigured work. They cannot create Products, change ownership, schedules
or workers, accept Ready/Done, or replace accepted instructions. Summary writes carry
the versions of all unarchived Non-recurring Tasks; stale source sets fail with 412.

## Migration and recovery

Version 3 combines prior purpose/outcome/description and acceptance text into
instructions, retains legacy lifecycle values, maps cancellation to archive and
removes board stages from direct work. IDs, comments and activity survive.
The current initializer includes run associations and schedule references. No migration runs on startup.
Back up Company and runtime databases before deployment. Restore both for run history.

Separate Company and runtime databases are supported without a distributed
transaction. A committed intent plus stable runtime ID recovers queue submission;
startup, scheduler ticks and history reads reconcile completed attempts. Default execution makes one
queue attempt; interrupted external work is visible rather than silently rerun.

The current examples are a bounded pilot. Live provider quality, multi-replica
operation and automatic workspace provisioning require separate deployment validation.


Cancellation covers queued and executing work. Cancellation before queue acceptance
is durable and prevents startup recovery or a request retry from dispatching that run.
While an executing worker stops, its status may remain running; poll until terminal.
Cancelling a run does not mark its Project Task Done. Apply the migration command
before starting this release. A fresh database uses the current initializer; version-5
pilot databases receive the Ready/review upgrade without enrolling existing Ready
Tasks. Reaccept those Tasks after returning to Backlog. Legacy In-review Tasks remain
manually acceptable; a fresh review is needed for automatic PR completion.


### Authenticated setup and repository source

`POST /company/v1/setup` accepts optional `repository: {url, branch}` and `agent_id`.
It requires a verified human with Company administration and an Idempotency-Key.
It returns the single built-in AgentOS Product; subsequent calls never reset it.
Products now include nullable `repository` and `builtin` fields. Product create/
patch support `repository`; only humans configure it. Tasks and run results include
nullable `source: {url, commit}` for the accepted immutable execution source.
Ready acceptance for a repository Task requires a sandboxed CodexAgent or
ClaudeAgent and installed sandbox repository workspace support. Repository Tasks
must belong to a Project so execution always has a review boundary.

## Files

- `GET /company/v1/files?product_id=<id>&directory=&query=&after=&limit=50` lists or searches files; follow `next_cursor` with `after`.
- `GET /company/v1/files/content?product_id=<id>&path=brief.md` returns content and version.
- `PUT /company/v1/files/content?product_id=<id>` accepts `{ "path": "brief.md", "content": "...", "expected_version": 0 }` and `Idempotency-Key`.

Omit `product_id` for Company-wide files. Product members share files; readers cannot
write. A stale version returns 412. Replaying the same write rechecks current access.
Task results are runtime-owned and cannot be overwritten by file tools. Files retain
exact whitespace. Company files are not exposed through agent-level filesystem routes.
