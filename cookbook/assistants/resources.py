from phi.docker.app.postgres import PgVectorDb

# -*- Run PgVector on port 5532 as port 5432 may be in use.
vector_db = PgVectorDb(
    pg_user="ai",
    pg_password="ai",
    pg_database="ai",
    host_port=5532,
)
