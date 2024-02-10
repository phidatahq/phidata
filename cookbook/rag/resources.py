from phi.docker.app.postgres import PgVectorDb
from phi.docker.resources import DockerResources

# -*- PgVector running on port 5432:5432
vector_db = PgVectorDb(
    pg_user="ai",
    pg_password="ai",
    pg_database="ai",
)

# -*- DockerResources
dev_docker_resources = DockerResources(apps=[vector_db])
