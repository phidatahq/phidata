"""Company-scoped text files using the framework database filesystem."""

import asyncio
import hashlib
import json
from dataclasses import asdict
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from sqlalchemy import func, select

from agno.fs import FileSystem
from agno.fs._paths import normalize_directory, normalize_path
from agno.fs.db import DbFileSystem
from agno.fs.errors import InvalidPathError
from agno.os.company.policy import CompanyError, Principal


class CompanyFiles:
    """Shared files with the same membership and transactions as Company work.

    Stores are never registered on an agent: every operation resolves access from
    its verified caller. File writes, idempotency and audit commit together.
    """

    def __init__(self, company: Any):
        self._company = company
        self._backend = DbFileSystem(db_engine=company._engine, db_schema="agno_company", table_name="files")

    def _store(self, product_id: Optional[str]) -> FileSystem:
        return FileSystem(self._backend, namespace=f"products/{UUID(product_id)}" if product_id else "company")

    def _access(self, conn: Any, principal: Principal, product_id: Optional[str], *, write: bool = False) -> None:
        if product_id:
            product = self._company._product(conn, principal, product_id, lock=write)
            if write:
                self._company._require(principal, product, "contributor", "write")
                if product["state"] != "active":
                    raise CompanyError(409, "archived", "Restore the Product before changing its files")
        else:
            if principal.product_id or not self._company._allowed(principal, "bootstrap" if write else "read"):
                raise CompanyError(403, "forbidden", "Company file access is not permitted")
            if write:
                from agno.os.company.service import _query

                _query(conn, "SELECT pg_advisory_xact_lock(741927105)")

    def _path(self, path: str, *, directory: bool = False) -> str:
        if path.startswith("/"):
            raise CompanyError(422, "invalid_path", "Use a relative file path inside this scope")
        try:
            return normalize_directory(path) if directory else normalize_path(path)
        except InvalidPathError as exc:
            raise CompanyError(422, "invalid_path", "Use a relative file path inside this scope") from exc

    def list(
        self,
        *,
        principal: Principal,
        product_id: Optional[str] = None,
        directory: str = "",
        query: str = "",
        after: str = "",
        limit: int = 50,
    ) -> Dict[str, Any]:
        """List or search permitted files with bounded, path-based pagination."""
        if not 1 <= limit <= 100 or len(query) > 500:
            raise CompanyError(422, "invalid_query", "Limit must be 1-100 and query at most 500 characters")
        directory = self._path(directory, directory=True)
        after = self._path(after) if after else ""
        store = self._store(product_id)
        t = self._backend.table
        with self._company._transaction(principal, read=True) as conn:
            self._access(conn, principal, product_id)
            stmt = select(t.c.path, t.c.version, t.c.size_bytes, t.c.updated_at).where(
                self._backend._key(store.namespace, ""),
                self._backend._directory_predicate(directory),
                t.c.path > after,
            )
            if query:
                stmt = stmt.where(func.strpos(func.lower(t.c.content), query.lower()) > 0)
            rows = [dict(row) for row in conn.execute(stmt.order_by(t.c.path).limit(limit + 1)).mappings()]
            return {"data": rows[:limit], "next_cursor": rows[limit - 1]["path"] if len(rows) > limit else None}

    async def alist(self, **kwargs: Any) -> Dict[str, Any]:
        return await asyncio.to_thread(self.list, **kwargs)

    def read(self, *, principal: Principal, path: str, product_id: Optional[str] = None) -> Dict[str, Any]:
        """Read a file and its current version in one snapshot."""
        path, store = self._path(path), self._store(product_id)
        t = self._backend.table
        with self._company._transaction(principal, read=True) as conn:
            self._access(conn, principal, product_id)
            row = (
                conn.execute(
                    select(t.c.path, t.c.content, t.c.version, t.c.size_bytes, t.c.updated_at).where(
                        self._backend._key(store.namespace, ""),
                        t.c.path == path,
                    )
                )
                .mappings()
                .first()
            )
            if row is None:
                raise CompanyError(404, "not_found", "File not found")
            return dict(row)

    async def aread(self, **kwargs: Any) -> Dict[str, Any]:
        return await asyncio.to_thread(self.read, **kwargs)

    def write(
        self,
        *,
        principal: Principal,
        path: str,
        content: str,
        expected_version: int,
        idempotency_key: str,
        request_id: str,
        product_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create with version 0 or replace the exact version previously read."""
        from agno.os.company.service import _json, _row

        path, store = self._path(path), self._store(product_id)
        size = len(content.encode("utf-8"))
        if expected_version < 0 or size > store.max_file_bytes:
            raise CompanyError(422, "invalid_file", "Use a nonnegative version and a file no larger than 1 MB")
        if not 1 <= len(idempotency_key) <= 200 or not 1 <= len(request_id) <= 200:
            raise CompanyError(422, "invalid_request_id", "Request identifiers must be 1-200 characters")
        operation = "file.write:" + store.namespace
        fingerprint = hashlib.sha256(_json([path, content, expected_version, principal.agent_id]).encode()).hexdigest()
        t = self._backend.table
        with self._company._transaction(principal) as conn:
            self._access(conn, principal, product_id, write=True)
            # Product mutations and file writes share the Product lock. Company-wide
            # writes share their advisory lock, including permission-checked retries.
            replay = _row(
                conn,
                "SELECT * FROM agno_company.idempotency WHERE principal_id=:who AND operation=:op AND key=:key",
                who=principal.id,
                op=operation,
                key=idempotency_key,
            )
            if replay:
                if replay["payload_hash"] != fingerprint:
                    raise CompanyError(409, "idempotency_conflict", "This request key already describes another write")
                return replay["result"]
            current = (
                conn.execute(
                    select(t.c.version, t.c.size_bytes)
                    .where(self._backend._key(store.namespace, ""), t.c.path == path)
                    .with_for_update()
                )
                .mappings()
                .first()
            )
            if (current["version"] if current else 0) != expected_version:
                raise CompanyError(412, "stale_file", "File changed; read its current version before writing")
            if product_id and path.split("/")[0] in ("projects", "tasks"):
                parts = path.split("/")
                if len(parts) < 3:
                    raise CompanyError(422, "invalid_path", "Use projects/<id>/<file> or tasks/<id>/<file>")
                if parts[0] == "tasks" and parts[2] == "results":
                    raise CompanyError(403, "immutable_result", "Run result files are written only by the runtime")
                try:
                    record_id = str(UUID(parts[1]))
                except ValueError as exc:
                    raise CompanyError(422, "invalid_path", "Use an existing Project or Task id") from exc
                record, _ = self._company._load(
                    conn, principal, "project" if parts[0] == "projects" else "task", record_id
                )
                if str(record["product_id"]) != str(product_id) or record["state"] != "active":
                    raise CompanyError(409, "invalid_parent", "Files must belong to active work in this Product")
            usage = conn.execute(
                select(func.coalesce(func.sum(t.c.size_bytes), 0)).where(self._backend._key(store.namespace, ""))
            ).scalar_one()
            if usage + size - (current["size_bytes"] if current else 0) > store.max_namespace_bytes:
                raise CompanyError(409, "file_quota", "This file scope has reached its storage limit")
            result = asdict(self._backend._write_on(conn, store.namespace, path, content))
            self._company._insert(
                conn,
                "activity",
                {
                    "id": str(uuid4()),
                    "product_id": product_id,
                    "subject_type": "file",
                    "subject_id": product_id or "00000000-0000-0000-0000-000000000000",
                    "actor_id": principal.agent_id or principal.id,
                    "initiating_principal_id": principal.id,
                    "operation": "file.write",
                    "delta": {
                        "path": path,
                        "version": result["version"],
                        "sha256": hashlib.sha256(content.encode()).hexdigest(),
                    },
                    "request_id": request_id,
                },
            )
            self._company._insert(
                conn,
                "idempotency",
                {
                    "principal_id": principal.id,
                    "operation": operation,
                    "key": idempotency_key,
                    "payload_hash": fingerprint,
                    "result": result,
                },
            )
            return json.loads(_json(result))

    async def awrite(self, **kwargs: Any) -> Dict[str, Any]:
        return await asyncio.to_thread(self.write, **kwargs)

    def _snapshot(
        self, conn: Any, principal: Principal, product_id: str, task_id: str, project_id: Optional[str]
    ) -> Dict[str, Any]:
        """Pin a bounded set of relevant text inputs in the durable dispatch payload."""
        t = self._backend.table
        namespaces = {self._store(product_id).namespace: "product"}
        if self._company._allowed(principal, "read"):
            namespaces["company"] = "company"
        result: Dict[str, Any] = {}
        size = 0
        for namespace, prefix in namespaces.items():
            stmt = select(t.c.path, t.c.content, t.c.version).where(self._backend._key(namespace, ""))
            if prefix == "product":
                from sqlalchemy import or_

                stmt = stmt.where(
                    or_(
                        ~t.c.path.startswith("tasks/"),
                        t.c.path.startswith(f"tasks/{task_id}/"),
                    )
                ).where(or_(~t.c.path.startswith("projects/"), t.c.path.startswith(f"projects/{project_id}/")))
            if prefix == "product":
                # Run history is available separately; copying it into every occurrence
                # would grow recurring-task context without bound.
                stmt = stmt.where(~t.c.path.startswith(f"tasks/{task_id}/results/"))
            rows = conn.execute(stmt.order_by(t.c.path).limit(101)).mappings()
            for row in rows:
                size += len(row["content"].encode("utf-8"))
                if len(result) >= 100 or size > 250_000:
                    raise CompanyError(
                        409,
                        "context_limit",
                        "Relevant Company files exceed the run context limit; archive or shorten them",
                    )
                result[f"{prefix}/{row['path']}"] = {"content": row["content"], "version": row["version"]}
        return result
