# Test log

### test_serialized_session_queue.py

**Status:** PASS

**Description:** Shared scenarios across in-memory, fakeredis, real Redis,
synchronous Postgres and asynchronous Postgres: contention, independent-session
progress, retry backoff, cancellation, stale-claim fencing, same-second acceptance
order and boolean-marker parity. Postgres-only cases cover an enqueue racing a
claimant that already selected its ticket, and claiming under an engine whose
default isolation is REPEATABLE READ. A fakeredis case forces 15 lost WATCH rounds
on one same-session submit.

**Result:** 32 passed, 11 skipped on local Postgres 14 and fakeredis. The skips are
real-Redis parameters (no `AGNO_TEST_REDIS_URL`) and the Postgres-only cases on other
stores. The original scenarios also passed on Postgres 16 and Redis 7. No model or
hosted-provider calls were made.

---

### test_external_queue_admission.py

**Status:** PASS

**Description:** Two distinct external-agent instances and queue workers execute
streaming/nonstreaming turns with pending history rows in reverse ticket order.

**Result:** Both cases passed; the waiting turn retains attempt 0 until admission,
then completes with attempt 1. Broader external-agent, queue, worker and wiring suite: 637 passed.

---
