"""Keep cancellation intent durable across partial dispatch and worker restart."""

SQL = """
ALTER TABLE agno_company.task_runs ADD COLUMN cancel_requested boolean NOT NULL DEFAULT false;
INSERT INTO agno_company.schema_version(version) VALUES(5);
"""
