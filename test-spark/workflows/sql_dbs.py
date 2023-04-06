from phidata.app.postgres import PostgresDb

from workflows.env import AIRFLOW_ENV
from workspace.dev.postgres import dev_postgres, dev_postgres_connection_id
from workspace.prd.postgres import prd_postgres, prd_postgres_connection_id

# -*- Postgres Apps

POSTGRES_APP: PostgresDb
if AIRFLOW_ENV == "prd":
    POSTGRES_APP = prd_postgres
else:
    POSTGRES_APP = dev_postgres


# -*- Postgres Connections

POSTGRES_CONN_ID: str
if AIRFLOW_ENV == "prd":
    POSTGRES_CONN_ID = prd_postgres_connection_id
else:
    POSTGRES_CONN_ID = dev_postgres_connection_id
