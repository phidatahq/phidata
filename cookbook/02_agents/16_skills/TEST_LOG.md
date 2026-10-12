# Test Log -- 16_skills

**Tested:** 2026-02-13
**Environment:** .venvs/demo/bin/python, pgvector: running

---

### basic_skills.py

**Status:** PASS
**Tier:** untagged
**Description:** Demonstrates basic skills. Ran successfully and produced expected output.
**Result:** Completed successfully in 8s.

---

### mcp_skills.py

**Status:** PASS
**Tier:** untagged
**Description:** Starts `mcp_skills_server.py` over stdio with `protocol_mode="auto"` (negotiated 2026-07-28) and loads its skills with `MCPSkills`. Listed `review-server/code-review` and `review-server/git-workflow` without reading content, then on demand the agent read `SKILL.md` and `references/style-guide.md`, each verified against the manifest digest and tagged `origin: mcp:review-server`. The model called `get_skill_script(..., execute=True)` and was refused, as MCP-served scripts are never executed. Tested on 2026-10-12 with `.venv/bin/python` and `gpt-5.6-luna`.
**Result:** Completed successfully with a structured code review.

---
