from datetime import timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.utils.dates import days_ago

# These args will get passed on to each operator
# You can override them on a per-task basis during operator initialization
default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "email": ["example@dag.com"],
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

distributed_dag = DAG(
    dag_id="distributed_dag",
    description="A distributed tutorial DAG",
    schedule_interval=timedelta(days=1),
    start_date=days_ago(2),
    default_args=default_args,
    tags=["example"],
)

echo_hostname_command = "echo $(hostname)"

task_1 = BashOperator(
    task_id="task_1",
    bash_command=echo_hostname_command,
    dag=distributed_dag,
)
task_2 = BashOperator(
    task_id="task_2",
    bash_command=echo_hostname_command,
    queue="tier_1",
    dag=distributed_dag,
)
task_3 = BashOperator(
    task_id="task_3",
    bash_command=echo_hostname_command,
    queue="tier_1",
    dag=distributed_dag,
)

# define dependencies
task_1 >> [task_2, task_3]
