"""Initial Company schema. Immutable once released; add a new version to evolve it."""

SQL = """
CREATE SCHEMA IF NOT EXISTS agno_company;
CREATE TABLE agno_company.schema_version (version integer PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE agno_company.products (
 id uuid PRIMARY KEY, key text NOT NULL UNIQUE, name text NOT NULL, purpose text NOT NULL,
 owner_id text NOT NULL, state text NOT NULL DEFAULT 'active' CHECK (state IN ('active','archived')),
 version integer NOT NULL DEFAULT 1 CHECK (version > 0),
 created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE agno_company.product_memberships (
 product_id uuid NOT NULL REFERENCES agno_company.products(id), principal_id text NOT NULL,
 role text NOT NULL CHECK (role IN ('reader','contributor','owner')), active boolean NOT NULL DEFAULT true,
 created_at timestamptz NOT NULL DEFAULT now(), PRIMARY KEY(product_id,principal_id)
);
CREATE TABLE agno_company.projects (
 id uuid PRIMARY KEY, key text NOT NULL UNIQUE, product_id uuid NOT NULL REFERENCES agno_company.products(id),
 title text NOT NULL, outcome text NOT NULL, acceptance_criteria text NOT NULL, owner_id text NOT NULL,
 status text NOT NULL DEFAULT 'proposed' CHECK (status IN ('proposed','active','on_hold','completed','canceled')),
 target_date date, completed_at timestamptz, version integer NOT NULL DEFAULT 1 CHECK(version > 0),
 created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(id,product_id), FOREIGN KEY(product_id,owner_id) REFERENCES agno_company.product_memberships(product_id,principal_id)
);
CREATE TABLE agno_company.tasks (
 id uuid PRIMARY KEY, key text NOT NULL UNIQUE, product_id uuid NOT NULL REFERENCES agno_company.products(id),
 project_id uuid, title text NOT NULL, description text NOT NULL DEFAULT '', acceptance_criteria text NOT NULL DEFAULT '',
 accountable_owner_id text, assignee_id text, status text NOT NULL DEFAULT 'backlog'
 CHECK (status IN ('backlog','ready','in_progress','in_review','done','canceled')),
 priority text NOT NULL DEFAULT 'normal' CHECK (priority IN ('low','normal','high','urgent')), due_date date,
 origin text NOT NULL DEFAULT 'human' CHECK(origin = 'human'), accepted_by text, accepted_at timestamptz,
 evidence jsonb NOT NULL DEFAULT '[]', completed_at timestamptz,
 version integer NOT NULL DEFAULT 1 CHECK(version > 0),
 created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(),
 FOREIGN KEY(project_id,product_id) REFERENCES agno_company.projects(id,product_id),
 FOREIGN KEY(product_id,accountable_owner_id) REFERENCES agno_company.product_memberships(product_id,principal_id),
 FOREIGN KEY(product_id,assignee_id) REFERENCES agno_company.product_memberships(product_id,principal_id),
 CHECK(status NOT IN ('ready','in_progress','in_review','done') OR
   (accepted_at IS NOT NULL AND accepted_by IS NOT NULL AND accountable_owner_id IS NOT NULL AND length(acceptance_criteria)>0))
);
CREATE TABLE agno_company.comments (
 id uuid PRIMARY KEY, project_id uuid REFERENCES agno_company.projects(id), task_id uuid REFERENCES agno_company.tasks(id),
 author_id text NOT NULL, body text NOT NULL, created_at timestamptz NOT NULL DEFAULT now(),
 CHECK ((project_id IS NULL) <> (task_id IS NULL))
);
CREATE TABLE agno_company.activity (
 id uuid PRIMARY KEY, product_id uuid NOT NULL REFERENCES agno_company.products(id),
 subject_type text NOT NULL, subject_id uuid NOT NULL, actor_id text NOT NULL, initiating_principal_id text NOT NULL,
 operation text NOT NULL, delta jsonb NOT NULL, request_id text NOT NULL, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE agno_company.idempotency (
 principal_id text NOT NULL, operation text NOT NULL, key text NOT NULL, payload_hash text NOT NULL,
 required_role text, required_action text, result jsonb NOT NULL, expires_at timestamptz NOT NULL DEFAULT now() + interval '7 days',
 created_at timestamptz NOT NULL DEFAULT now(), PRIMARY KEY(principal_id,operation,key)
);
CREATE INDEX company_members_principal ON agno_company.product_memberships(principal_id,product_id) WHERE active;
CREATE INDEX company_projects_product ON agno_company.projects(product_id,created_at,id);
CREATE INDEX company_tasks_product ON agno_company.tasks(product_id,created_at,id);
CREATE INDEX company_tasks_project ON agno_company.tasks(project_id,created_at,id);
CREATE INDEX company_activity_product ON agno_company.activity(product_id,created_at,id);
CREATE INDEX company_comments_project ON agno_company.comments(project_id,created_at,id);
CREATE INDEX company_comments_task ON agno_company.comments(task_id,created_at,id);

-- Enforce the accountable Product owner even for non-service SQL writers.
CREATE FUNCTION agno_company.require_product_owner() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE pid uuid;
BEGIN
 IF TG_TABLE_NAME = 'products' THEN pid := NEW.id; ELSE pid := COALESCE(NEW.product_id, OLD.product_id); END IF;
 IF EXISTS (SELECT 1 FROM agno_company.products p WHERE p.id=pid AND NOT EXISTS (
   SELECT 1 FROM agno_company.product_memberships m WHERE m.product_id=p.id
    AND m.principal_id=p.owner_id AND m.role='owner' AND m.active)) THEN
   RAISE EXCEPTION 'Product requires active owner membership' USING ERRCODE='23514';
 END IF;
 RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER company_owner_product AFTER INSERT OR UPDATE ON agno_company.products
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION agno_company.require_product_owner();
CREATE CONSTRAINT TRIGGER company_owner_member AFTER INSERT OR UPDATE OR DELETE ON agno_company.product_memberships
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION agno_company.require_product_owner();
INSERT INTO agno_company.schema_version(version) VALUES(1);
"""
