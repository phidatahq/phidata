from agno.docker.app.postgres.pgvector import PgVectorDb


pgvector = PgVectorDb(
    name="pgvector",
    pg_user="agno",
    pg_password="agno",
    pg_database="agno",
    # Connect to this db on port 9320
    host_port=9320,
)
