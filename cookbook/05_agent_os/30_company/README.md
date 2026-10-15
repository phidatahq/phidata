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
The HTTP layer derives ownership from authenticated identity. With isolation
on, another owner's Product is invisible and returns 404, including on writes.
With isolation off, callers with the required scope can read and change every
Product. Admins bypass owner isolation.
