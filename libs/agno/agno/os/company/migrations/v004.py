"""Task execution references and recurring-task configuration."""

SQL = """
ALTER TABLE agno_company.tasks ADD COLUMN schedule jsonb;
ALTER TABLE agno_company.tasks ADD COLUMN schedule_principal jsonb;
ALTER TABLE agno_company.tasks ADD COLUMN schedule_id text;
ALTER TABLE agno_company.tasks DROP CONSTRAINT tasks_origin_check;
ALTER TABLE agno_company.tasks ADD CONSTRAINT task_origin CHECK(origin IN ('human','agent'));
CREATE TABLE agno_company.task_runs (
 id uuid PRIMARY KEY, task_id uuid NOT NULL REFERENCES agno_company.tasks(id),
 task_version integer NOT NULL, agent_id text NOT NULL, initiating_principal_id text NOT NULL,
 principal jsonb NOT NULL, payload jsonb NOT NULL, request_hash text NOT NULL,
 session_id text NOT NULL, trigger text NOT NULL CHECK(trigger IN ('manual','schedule','agent')),
 released boolean NOT NULL DEFAULT false, skipped boolean NOT NULL DEFAULT false,
 created_at timestamptz NOT NULL DEFAULT now(), reconciled_at timestamptz
);
CREATE UNIQUE INDEX company_one_active_run ON agno_company.task_runs(task_id) WHERE NOT released;
CREATE INDEX company_task_runs ON agno_company.task_runs(task_id,created_at DESC,id);
INSERT INTO agno_company.schema_version(version) VALUES(4);
"""
