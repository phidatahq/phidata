"""Run using `ag start cookbook/infra/docker/pgvector.py`"""

from agno.docker.app.postgres.pgvector import PgVectorDb


pgvector = PgVectorDb(
    name="pgvector",
    pg_user="agno",
    pg_password="agno",
    pg_database="agno",
    # Connect to this db on port 5432
    host_port=5432,
)
