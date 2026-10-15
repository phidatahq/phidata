"""Product repositories and source pinned by human Ready acceptance."""

SQL = """
ALTER TABLE agno_company.products ADD COLUMN repository jsonb;
ALTER TABLE agno_company.products ADD COLUMN builtin text UNIQUE CHECK (builtin = 'agentos');
ALTER TABLE agno_company.tasks ADD COLUMN source jsonb;
INSERT INTO agno_company.schema_version(version) VALUES (7);
"""
