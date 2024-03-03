from phi.docker.app.postgres import PgVectorDb
from phi.docker.resources import DockerResources

# -*- PgVector running on port 5532:5432
vector_db = PgVectorDb(
    name="cookbook-db",
    pg_user="ai",
    pg_password="ai",
    pg_database="ai",
    host_port=5532,
)

# -*- DockerResources
dev_docker_resources = DockerResources(apps=[vector_db])
