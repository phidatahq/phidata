# Test log: Vercel sandbox cookbook

What the Vercel sandbox provider's tests cover, how they are gated, and what has been run. Counts were measured on macOS with Python 3.12 and `vercel-sandbox` 0.9.0 (importable, or not, as stated); they describe the files in this tree and will change as the tests do.

### vercel_session.py

**Status:** NOT RUN

**Description:** The example needs Vercel credentials and creates billable computers. No mode of it has been executed against Vercel.

**Result:** No claim is made about its behavior on Vercel.

---

### unit tests: libs/agno/tests/unit/sandbox/test_vercel.py

**Status:** PASS

**Description:** The provider against a fake of the Vercel SDK: command and runtime requests (no replay, exact-session stop, pre-send credential errors, bounded output, client cleanup), discovery by prefix with complete pagination and tag/configuration checks, creation with bootstrap and cleanup, destruction with an ownership recheck, and the checkpoint transfer. It also runs the orchestration helpers the live tests use (adoption counting, cancellation at bootstrap entry, killing a capture while the agent is frozen) against scripted fakes, with negative controls, and the live recovery adapter (`SdkGuest`) against a fake SDK, which checks the test code and not the real SDK's behavior. A Codex home with a plugin clone larger than the checkpoint limit is captured without the clone and restores onto a fresh guest, while other data over the limit is still refused. Public mode gives a Claude or Codex harness only that harness's key in the computer's environment. The guest guard runs on a temporary directory standing in for the guest, through its own entry points: admission and recovery, the freeze journal, capture, restore, bootstrap finish, the source digest and the agent environment. Process control uses a scripted process table and a fixture `/proc`.

**Result:**
- With the SDK importable: 461 passed, 1 skipped (the live-kernel process test, which skips off Linux).
- Without the SDK: 451 passed, 11 skipped (the same test plus 10 that import the SDK).
- The whole `libs/agno/tests/unit/sandbox` directory: 955 passed, 9 skipped with the SDK; 945 passed, 19 skipped without it. The skips outside this file are environmental (`boto3`, `claude_agent_sdk`, `openai_codex`).

---

### integration tests: libs/agno/tests/integration/sandbox/test_vercel.py

**Status:** PARTIAL: 4 of 25 tests have a recorded hosted run

**Description:** 25 tests that create billable Vercel computers. The whole module is skipped unless `AGNO_TEST_VERCEL=1` and `AGNO_TEST_VERCEL_WHEEL` (a wheel built from this checkout with `cd libs/agno && uv build --wheel`) are set. Seven tests need more: the three public-path tests (P3, P3 with attachments, P4) and the four native-recall tests need `AGNO_TEST_SANDBOX_DB_URL` for Postgres, and the recall tests also need a model key (`ANTHROPIC_API_KEY` or `CLAUDE_CODE_OAUTH_TOKEN` for Claude, `OPENAI_API_KEY` for Codex).

The four tests that recall a native conversation (Claude and Codex, each on a restored computer after a forced-cold public restore and on a reused warm computer) each passed once against Vercel on 2026-10-22, using a wheel built from this tree (agno 3.1.8, source digest `25206570a90898862109f170e355b6f9c72663edd09b902bb032ac58d8c2dd9c`), with Postgres and real model keys. The computers they created were deleted and confirmed gone by a direct read.

The other 21 have not been run against Vercel on this tree: bootstrap and the pinned natives, the guard's privilege drop and control paths, the file API's ownership and mode, command timeout, unicode and binary stdin, tag round trip and listing, stale-handle destroy, adoption, cancelled create, identity values, P1, runtime worker lifetime, P2, refusal of a restore onto a used computer, recovery of a killed capture, writer classes a capture must stop, real process handles, and the public P3, P3 with attachments and P4.

**Result:** Offline, with the SDK importable and no gate variables set, all 25 are collected and skipped. The four recall tests are single hosted runs, not a statement about timing or behavior elsewhere.

---

### hosted fixture runs (separate harness, outside this repository)

**Status:** PASS for the paths listed; these runs did not execute the test files in this directory

**Description:** On 2026-10-22, against Vercel with SDK 0.9.0 and the same wheel. With the fixture runtime and no model: absolute and relative symlinks surviving a capture and restore onto a fresh computer; retention of the newest two checkpoints and a session delete that leaves no objects or computers; a permanent content error that leaves the binding on the last good checkpoint; and a computer that expires on its lifetime. With real models: one native Claude and one native Codex conversation each continued on one computer, was captured, and recalled a fact after a restore onto a fresh computer with the earlier computer deleted.

**Result:** One run of each. They do not cover the public `sandbox=` path beyond the four tests above, and they exercised no crash case.

---

### packaging

**Status:** PASS for what is stated

**Description:** `libs/agno/pyproject.toml` adds the `vercel-sandbox` extra (`vercel-sandbox>=0.9.0,<0.10`, unmarked so it fails on Python 3.9) and includes it in `dev` for Python 3.10 and later. A wheel built from the tree contains the four provider modules, and the digest of its unpacked `agno/` equals the digest of the source tree.

**Result:** Dependency resolution of the `vercel-sandbox`, `dev` and `tests` extras on Python 3.9, 3.10 and 3.12 was checked when the extra was added and has not been repeated since; no installation of the extra into an environment has been done as part of this log.

---

### formatting and type checking

**Status:** PASS

**Description:** `ruff check`, `ruff format --check` and the import sort (`ruff check --select I`) on the provider package, both test files and this directory, and `mypy` on the four provider modules with the SDK importable. The commands of `./scripts/validate.sh` for `libs/agno` and `cookbook` (`ruff check`, `mypy`) were also run on this tree and on the commit it is based on, with the same interpreter and configuration.

**Result:** All clean on the files above. Tests are excluded from the repository's mypy configuration. `ruff check` is clean for `libs/agno` and `cookbook`. `mypy libs/agno` reports the same 39 errors in 11 files before and after (compared as sorted, line-normalized lists), none in `sandbox/vercel`; with the SDK on the path it reports 59 before and after, also identical. The `agnoctl` step and the cookbook pattern check were not run. No test is run by these commands.

---

## Not run

- The 21 integration tests listed above, against Vercel: among them the install inside the coordinator transaction, tag value limits, listing delay after create, the real owner and mode of a staged file, `lifetime` enforcement, stale destroy against the real service, a lost create reply, and real process control on a Linux kernel (privilege drop, `no_new_privs`, freezing of plain, child, session-changed and double-fork writers, recovery of a capture killed while frozen). PID reuse is unsupported on Vercel and is not forced.
- A restore across different native versions, and a restore of an archive larger than a few tens of MiB.
- CI: no run of any workflow has happened for this change.
