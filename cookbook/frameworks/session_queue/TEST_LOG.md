# Test log

### test_serialized_session_queue.py

**Status:** PASS

**Description:** Five shared scenarios across in-memory, fakeredis, real Redis,
synchronous Postgres and asynchronous Postgres: contention, independent-session
progress, retry backoff, cancellation and stale-claim fencing.

**Result:** 31 cases passed on dedicated local Postgres 16 and Redis 7, including a
controlled concurrent enqueue/claim race and strict boolean-marker parity. Four
parameter combinations skip the PostgreSQL-specific controlled interleaving.
No model or hosted-provider calls were made.

---

### test_external_queue_admission.py

**Status:** PASS

**Description:** Two distinct external-agent instances and queue workers execute
streaming/nonstreaming turns with pending history rows in reverse ticket order.

**Result:** Both cases passed; the waiting turn retains attempt 0 until admission,
then completes with attempt 1. Broader external-agent, queue, worker and wiring suite: 637 passed.

---
