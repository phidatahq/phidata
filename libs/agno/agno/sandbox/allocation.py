"""Durable allocation intent for providers without atomic create-by-name APIs."""

import hashlib
from typing import Any, Dict, Optional, Tuple
from uuid import uuid4

from sqlalchemy import BigInteger, Column, MetaData, String, Table, func, select, text, update
from sqlalchemy.dialects.postgresql import insert

from agno.sandbox.base import SandboxError
from agno.sandbox.postgres import PostgresSandboxStore


class SandboxAllocationUnknown(SandboxError):
    """A create may have reached the provider; reconcile before another allocation."""


class SandboxCapacityExceeded(SandboxError):
    """The configured deployment allocation limit includes active and uncertain creates."""


class PostgresAllocationJournal:
    """Control-plane journal; never pass its database credentials to compute.

    Reserve commits before sending create. An uncertain create remains pending
    until inventory finds the exact token. Absence from a list is not proof that
    a delayed request cannot still allocate, so pending intents are not expired
    or automatically retried. Confirmed destruction permits a new allocation.
    All replicas in a namespace must configure the same capacity limit.
    """

    def __init__(self, store: PostgresSandboxStore, *, table_name: str = "agno_sandbox_allocations") -> None:
        if not table_name.isidentifier() or len(table_name) > 63:
            raise ValueError("Allocation table must be a PostgreSQL identifier")
        self.store = store
        self.table = Table(
            table_name,
            MetaData(schema=store.bindings.schema),
            Column("namespace", String(128), primary_key=True),
            Column("name", String(128), primary_key=True),
            Column("digest", String(64), nullable=False),
            Column("token", String(32), nullable=False),
            Column("state", String(16), nullable=False),
            Column("provider_ref", String(512)),
            Column("updated_at", BigInteger, nullable=False),
        )

    async def _transaction(self, operation: Any) -> Any:
        def execute(connection: Any) -> Any:
            # A waiting capacity claimant must see the preceding claimant's
            # committed row even when the engine defaults to REPEATABLE READ.
            connection.execute(text("SET TRANSACTION ISOLATION LEVEL READ COMMITTED"))
            return operation(connection)

        return await self.store._transaction(execute)

    async def asetup(self) -> None:
        def create(connection: Any) -> None:
            key = int.from_bytes(hashlib.sha256(self.table.fullname.encode()).digest()[:8], "big", signed=True)
            connection.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": key})
            self.table.create(connection, checkfirst=True)

        await self._transaction(create)

    def setup(self) -> None:
        self.store._sync(self.asetup)

    def _key(self, namespace: str, name: str) -> Any:
        return (self.table.c.namespace == namespace) & (self.table.c.name == name)

    async def ainspect(self, namespace: str, name: str) -> Optional[Dict[str, Any]]:
        def read(connection: Any) -> Optional[Dict[str, Any]]:
            row = connection.execute(select(self.table).where(self._key(namespace, name))).mappings().first()
            return dict(row) if row is not None else None

        return await self._transaction(read)

    def inspect(self, namespace: str, name: str) -> Optional[Dict[str, Any]]:
        return self.store._sync(self.ainspect, namespace, name)

    async def _reserve(
        self, namespace: str, name: str, digest: str, *, max_allocations: int
    ) -> Tuple[Dict[str, Any], bool]:
        if not namespace or len(namespace) > 128 or not name or len(name) > 128 or len(digest) != 64:
            raise ValueError("Allocation identity must be bounded")
        if type(max_allocations) is not int or max_allocations < 1:
            raise ValueError("Allocation capacity must be a positive integer")

        def reserve(connection: Any) -> Tuple[Dict[str, Any], bool]:
            # This also serializes capacity accounting across distinct sessions.
            key = int.from_bytes(
                hashlib.sha256((self.table.fullname + namespace).encode()).digest()[:8], "big", signed=True
            )
            connection.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": key})
            row = (
                connection.execute(select(self.table).where(self._key(namespace, name)).with_for_update())
                .mappings()
                .first()
            )
            if row is not None:
                if row["digest"] != digest:
                    raise SandboxError("Allocation generation configuration changed")
                if row["state"] != "retired":
                    return dict(row), False
            count = connection.execute(
                select(func.count())
                .select_from(self.table)
                .where(self.table.c.namespace == namespace, self.table.c.state != "retired")
            ).scalar_one()
            if count >= max_allocations:
                raise SandboxCapacityExceeded("Hosted allocation capacity is exhausted; pending creates also count")
            values = dict(
                namespace=namespace,
                name=name,
                digest=digest,
                token=uuid4().hex,
                state="pending",
                provider_ref=None,
                updated_at=func.extract("epoch", func.clock_timestamp()).cast(BigInteger),
            )
            if row is None:
                result = connection.execute(insert(self.table).values(**values).returning(self.table)).mappings().one()
            else:
                result = (
                    connection.execute(
                        update(self.table).where(self._key(namespace, name)).values(**values).returning(self.table)
                    )
                    .mappings()
                    .one()
                )
            return dict(result), True

        return await self._transaction(reserve)

    async def _bind(self, namespace: str, name: str, token: str, provider_ref: str) -> None:
        if not provider_ref or len(provider_ref) > 512:
            raise ValueError("Provider reference must be bounded")

        def bind(connection: Any) -> None:
            row = (
                connection.execute(select(self.table).where(self._key(namespace, name)).with_for_update())
                .mappings()
                .first()
            )
            if row is None or row["token"] != token or row["state"] == "retired":
                raise SandboxAllocationUnknown("Allocation intent was superseded")
            if row["provider_ref"] not in (None, provider_ref):
                raise SandboxAllocationUnknown("One allocation intent produced conflicting provider identities")
            connection.execute(
                update(self.table)
                .where(self._key(namespace, name))
                .values(
                    provider_ref=provider_ref,
                    state="ready",
                    updated_at=func.extract("epoch", func.clock_timestamp()).cast(BigInteger),
                )
            )

        await self._transaction(bind)

    async def _retire(self, namespace: str, name: str, token: str, provider_ref: str) -> None:
        def retire(connection: Any) -> None:
            result = connection.execute(
                update(self.table)
                .where(
                    self._key(namespace, name), self.table.c.token == token, self.table.c.provider_ref == provider_ref
                )
                .values(state="retired", updated_at=func.extract("epoch", func.clock_timestamp()).cast(BigInteger))
            )
            if result.rowcount != 1:
                raise SandboxAllocationUnknown("Cannot retire an unconfirmed or superseded allocation")

        await self._transaction(retire)
