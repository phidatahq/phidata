# Queued external-agent session admission

AgentOS marks durably queued Claude/Codex turns for session serialization. With
the built-in Postgres, Redis or development in-memory queue, one active ticket per
component session is admitted. Other sessions can run concurrently. Waiting turns
remain queued and do not consume attempts or worker slots; an earlier turn's retry
backoff also holds later turns. Cancellation and exhausted-job reconciliation
release the next eligible turn.

Queue order is `(created_at, id)`, with the ID breaking same-second ties. It is not
a promise of wall-clock HTTP arrival order. Session run rows can be persisted in a
different order, so execution follows the elected queue ticket rather than the
order of pending history rows. Active RUNNING rows still protect against an
already-running direct call.

This change does not provide cross-replica admission for direct/nonqueued calls,
native-state fencing or filesystem isolation. Do not mix direct concurrent turns
with queued turns in the same session. Those require the shared runtime ownership
contract. Third-party queue stores must implement serialization and explicitly
advertise `serializes_sessions = True` before the worker trusts their election.

Upgrade queue workers together before relying on this behavior; old workers do
not enforce the new contract. Drain existing unmarked tickets before switching.
Postgres serialized claiming requires READ COMMITTED transaction isolation.
Redis's per-session active index is updated atomically with job records; preserve
both in backups and configure appropriate Redis persistence for durability.

Run credential-free local tests:

```bash
.venv/bin/python -m pytest libs/agno/tests/unit/agents/test_external_queue_admission.py -q
.venv/bin/python -m pytest libs/agno/tests/integration/db/test_serialized_session_queue.py -q
```

The second command tests in-memory and fakeredis locally. Set
`AGNO_TEST_POSTGRES_URL` and `AGNO_TEST_REDIS_URL` to disposable local test services
to enable real Postgres (sync/async) and Redis scenarios. Each test uses its own
random table or prefix and removes only its own test records.
