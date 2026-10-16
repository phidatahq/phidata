---
name: refresh
description: Refresh Product status from current work and source evidence.
---

Read the Product identified in the message. Read its playbook,
Projects and Tasks, then inspect configured Sources with read_company_source.
Reflect observed progress and failures in status.md using its current version.
On a conflict, read again and incorporate intervening changes. Propose changes
for human review; never accept work or mark a Task Ready or Done.
If nothing changed, return a quiet successful check without writing duplicate pages.

For each Source, call read_company_source without path for a paged, content-free
index. Use pattern and next_offset to narrow discovery. Pass a returned path to
read one document; next_content_offset continues large documents. Compare the
full-document content_hash across fragments and reread if it changes. Never infer
content from an index entry. Use intake_company_source for Task proposals;
propose_company_task is unavailable to Routines.
