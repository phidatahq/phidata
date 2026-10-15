# Test Log: Company Products

### 01_manage_products.py

**Status:** PASS

**Description:** Ran `cookbook/05_agent_os/30_company/01_manage_products.py`
with the clean development environment on October 15, 2026. SQLite persistence,
two users, unscoped and owner-filtered listings, soft delete, include_deleted,
and restore were exercised without a model or provider calls.

**Result:** All assertions passed. Output:

```text
Isolation off: 2 Products
Isolation on for alice: 1 Product
Soft delete, include_deleted and restore passed
```

---
