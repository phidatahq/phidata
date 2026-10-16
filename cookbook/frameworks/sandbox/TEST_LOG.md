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
