"""Simplify work records while preserving earlier instructions and lifecycle history."""

SQL = """
ALTER TABLE agno_company.products RENAME COLUMN purpose TO instructions;
ALTER TABLE agno_company.products ADD COLUMN agent_id text;
ALTER TABLE agno_company.projects ADD COLUMN state text NOT NULL DEFAULT 'active' CHECK(state IN ('active','archived'));
ALTER TABLE agno_company.projects ADD COLUMN instructions text NOT NULL DEFAULT '';
UPDATE agno_company.projects SET instructions = concat_ws(E'\n\n', nullif(outcome,''),
 CASE WHEN acceptance_criteria <> '' THEN 'Acceptance checks: ' || acceptance_criteria END),
 state=CASE WHEN status='canceled' THEN 'archived' ELSE 'active' END;
ALTER TABLE agno_company.projects RENAME COLUMN status TO legacy_status;
ALTER TABLE agno_company.projects DROP COLUMN outcome, DROP COLUMN acceptance_criteria;
ALTER TABLE agno_company.projects ADD COLUMN summary text NOT NULL DEFAULT '';
ALTER TABLE agno_company.projects ADD COLUMN summary_at timestamptz;
ALTER TABLE agno_company.projects ADD COLUMN summary_sources jsonb NOT NULL DEFAULT '{}';
ALTER TABLE agno_company.tasks ADD COLUMN state text NOT NULL DEFAULT 'active' CHECK(state IN ('active','archived'));
ALTER TABLE agno_company.tasks ADD COLUMN agent_id text;
ALTER TABLE agno_company.tasks ADD COLUMN legacy_status text;
ALTER TABLE agno_company.tasks ADD COLUMN instructions text NOT NULL DEFAULT '';
ALTER TABLE agno_company.tasks DROP CONSTRAINT tasks_check;
ALTER TABLE agno_company.tasks DROP CONSTRAINT tasks_status_check;
ALTER TABLE agno_company.tasks ALTER COLUMN status DROP NOT NULL, ALTER COLUMN status DROP DEFAULT;
UPDATE agno_company.tasks SET legacy_status=status,
 instructions=concat_ws(E'\n\n', nullif(description,''),
 CASE WHEN acceptance_criteria <> '' THEN 'Acceptance checks: ' || acceptance_criteria END),
 state=CASE WHEN status='canceled' THEN 'archived' ELSE 'active' END,
 status=CASE WHEN project_id IS NULL THEN NULL WHEN status='canceled' THEN 'backlog' ELSE status END;
ALTER TABLE agno_company.tasks DROP COLUMN description, DROP COLUMN acceptance_criteria;
ALTER TABLE agno_company.tasks ADD CONSTRAINT task_stage CHECK (
 (project_id IS NULL AND status IS NULL) OR
 (project_id IS NOT NULL AND status IS NOT NULL AND status IN ('backlog','ready','in_progress','in_review','done')));
ALTER TABLE agno_company.tasks ADD CONSTRAINT task_acceptance CHECK (
 status IS NULL OR status='backlog' OR
 (accepted_at IS NOT NULL AND accepted_by IS NOT NULL AND accountable_owner_id IS NOT NULL AND length(instructions)>0));
INSERT INTO agno_company.schema_version(version) VALUES(3);
"""
