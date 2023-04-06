from phidata.app.group import AppGroup
from phidata.app.postgres import PostgresDb

from workspace.settings import ws_settings

# -*- Run a postgres database on docker

# Dev postgres: A postgres instance to use for dev data
dev_postgres = PostgresDb(
    name=f"postgres-{ws_settings.ws_name}",
    db_user=ws_settings.ws_name,
    db_password=ws_settings.ws_name,
    db_schema=ws_settings.ws_name,
    # Connect to this db on port 8315
    container_host_port=8315,
    use_cache=ws_settings.use_cache,
)

dev_postgres_connection_id = "dev_postgres"
dev_postgres_airflow_connections = {
    dev_postgres_connection_id: dev_postgres.get_db_connection_url_docker()
}

dev_postgres_apps = AppGroup(
    name="postgres",
    enabled=ws_settings.dev_postgres_enabled,
    apps=[dev_postgres],
)
