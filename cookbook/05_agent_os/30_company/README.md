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
These examples manage records only and do not execute agents. Registry
validation and run dispatch arrive with execution support.

Project and Task HTTP reads are company-wide for callers with the resource's
read scope, matching Products. With user isolation enabled, writes and
transitions require ownership; a visible foreign record returns 403. Admins
and callers on deployments with isolation disabled retain unscoped writes.
New work can use another owner's Product or Project, with the Task and
Project still required to belong to the same Product. Manager and storage
methods retain explicit owner filters for direct callers.
