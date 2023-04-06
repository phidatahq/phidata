from os import getenv

# -*- The AIRFLOW_ENV env variable pulls the airflow runtime environment
# Expected values: `dev`, `stg` or `prd`
AIRFLOW_ENV: str = getenv("AIRFLOW_ENV", "dev")
