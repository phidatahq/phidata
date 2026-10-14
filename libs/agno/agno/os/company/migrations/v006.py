"""Persist Ready authority and a reviewer-approved pull request revision."""

SQL = """
ALTER TABLE agno_company.tasks ADD COLUMN ready_principal jsonb;
ALTER TABLE agno_company.tasks ADD COLUMN ready_agent_id text;
ALTER TABLE agno_company.tasks ADD COLUMN review_pull_request jsonb;
ALTER TABLE agno_company.tasks ADD COLUMN review_principal jsonb;
ALTER TABLE agno_company.tasks ADD COLUMN review_started_at timestamptz;
ALTER TABLE agno_company.tasks ADD COLUMN automation_error text;
ALTER TABLE agno_company.task_runs DROP CONSTRAINT task_runs_trigger_check;
ALTER TABLE agno_company.task_runs ADD CONSTRAINT task_runs_trigger_check
 CHECK(trigger IN ('manual','schedule','agent','ready'));
INSERT INTO agno_company.schema_version(version) VALUES(6);
"""
