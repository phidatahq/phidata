from phi.docker.app.postgres import PgVectorDb

# -*- PgVector running on port 5532:5432
vector_db = PgVectorDb(
    name="phi-pgvector",
    pg_user="ai",
    pg_password="ai",
    pg_database="ai",
    host_port=5532,
)
