from phi.docker.app.singlestore import s2VectorDb
from phi.docker.resources import DockerResources

# -*- s2Vector running on port 3306:3306
vector_db = s2VectorDb(
    s2_user="ai",
    s2_password="ai",
    s2_database="ai",
    debug_mode=True,
)

# -*- DockerResources
dev_docker_resources = DockerResources(apps=[vector_db])
