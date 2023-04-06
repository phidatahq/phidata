from pathlib import Path

from airflow.models import DAG
from airflow.providers.papermill.operators.papermill import PapermillOperator
from airflow.utils.dates import days_ago

DAG_ID = "notebooks_daily"
EMAILS = ["alerts@datateam.com"]

default_task_args = {
    "owner": "airflow",
    "depends_on_past": True,
    "start_date": days_ago(1),
    "email": EMAILS,
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 1,
}

workflows_dir = Path(__file__).parent.parent
notebooks_dir = workflows_dir.parent.joinpath("notebooks")

with DAG(
    dag_id=DAG_ID,
    description="Run notebooks daily",
    default_args=default_task_args,
    tags=["notebooks"],
    catchup=False,
) as dag:
    hello_world = PapermillOperator(
        task_id="hello_world",
        input_nb=str(notebooks_dir.joinpath("examples", "hello_world.ipynb")),
        output_nb="/tmp/hello_world_{{ execution_date }}.ipynb",
        parameters={"msg": "Ran from Airflow at {{ execution_date }}!"},
    )
