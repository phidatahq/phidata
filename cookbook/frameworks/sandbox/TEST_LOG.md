# Sandbox cookbook test log

## October 16, 2026: agent repository configuration

### repository_workspace.py

**Status:** PASS

**Description:** Imported `cookbook/frameworks/sandbox/repository_workspace.py` with a test PostgreSQL URL, explicit checkpoint directory, runtime image, and public GitHub repository. Constructed the agent and inspected its runtime submission configuration.

**Result:** `repository=Repository(url, branch)` reached `config.repository`; no per-run repository option was needed. This was a construction/configuration smoke test, without a live Codex or Claude model call.

---

### Repository and external-agent regression suites

**Status:** PASS

**Description:** Ran `libs/agno/tests/unit/sandbox` and `libs/agno/tests/unit/agents` using the development environment and a temporary dummy AWS profile.

**Result:** 1,030 passed; one existing deprecation warning. Repository cases cover local Git branch resolution, shallow detached checkout, engineer commits and edits across resume/replacement, missing and mismatched markers, configuration validation without subprocess/network calls, both harness cwd settings, sync/async run rejection, configuration fingerprints, fixed errors, cancellation drain, and cleanup. Credential checks inspect argv, workspace/runtime files, error text, and captured checkpoint bytes for both raw and encoded token leakage.

---

### Repository integration

**Status:** PASS

**Description:** Ran PostgreSQL state-store tests, repository coordinator checks with a Docker runtime containing the feature source, and the opt-in public GitHub fetch.

**Result:** 122 distinct PostgreSQL cases passed across sync/async adapters, with 12 existing conditional skips, counted across the full run and corrected fixture rerun. Four Docker/PostgreSQL repository cases passed: retryable preparation failure plus live public checkout, warm reuse, cold replacement, edit/pin retention, and changed/removed configuration refusal. One standalone `live` public GitHub fetch passed without credentials. Run metadata matched the marker. No private GitHub or live model calls were made.

---

### Format and validation

**Status:** PASS

**Description:** Ran the full `scripts/format.sh` and `scripts/validate.sh`; removed unrelated baseline formatter changes from the feature diff.

**Result:** Format passed. Full validation passed in the existing clean Python 3.10 environment. Development Python 3.12 validation reported the same 40 errors in 14 files as untouched main `ab0e2d233a`, with identical diagnostics and zero introduced. `git diff --check` passed.

---

## October 16, 2026: first-turn metadata override

### Repository metadata overrides and transport

**Status:** PASS

**Description:** Added `metadata.repository` with exactly one full commit SHA or valid branch name. Validation refuses URL overrides before Git/network access. The first turn uses the override; later turns and restored computers retain the marker's pin. A branch override records its effective branch and retains the original configured branch internally for configuration mismatch checks.

**Result:** All 511 sandbox unit tests passed. Tests cover old-commit checkout after the default branch advances, a different branch, same/different later overrides, restored checkpoints, URL refusal, and sync/async harness, coordinator, and runtime-client forwarding. Six PostgreSQL cases passed across both adapters for default, commit, and branch pin publication. One live AgentOS route/Redis/PostgreSQL/Docker test passed: middleware `request.state.metadata` reaches the queued payload and runtime, the requested commit is published, later overrides are ignored, and a URL override returns 400 before allocation. No live model calls.

---

### Override format and validation

**Status:** PASS

**Description:** Ran the full format script and full validation script in the clean Python 3.10 environment after the forwarding changes.

**Result:** Both passed; `git diff --check` passed. Unrelated baseline formatter edits were removed. The earlier development-environment baseline comparison above belongs to the initial revision and was not rerun for this addition.

---
