from datetime import timedelta
from textwrap import dedent

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

simple_dag = DAG(
    dag_id="simple_dag",
    default_args=default_args,
    description="A simple tutorial DAG",
    schedule_interval=timedelta(days=1),
    start_date=days_ago(2),
    tags=["example"],
)

# t1, t2 and t3 are examples of tasks
task_1 = BashOperator(
    task_id="print_date",
    bash_command="date",
    dag=simple_dag,
)

task_2 = BashOperator(
    task_id="sleep",
    depends_on_past=False,
    bash_command="sleep 5",
    retries=3,
    dag=simple_dag,
)

templated_command = dedent(
    """
{% for i in range(5) %}
    echo "{{ ds }}"
    echo "{{ macros.ds_add(ds, 7)}}"
    echo "{{ params.my_param }}"
{% endfor %}
"""
)
task_3 = BashOperator(
    task_id="templated",
    depends_on_past=False,
    bash_command=templated_command,
    params={"my_param": "my_parameter"},
    dag=simple_dag,
)

# define dependencies
task_1 >> [task_2, task_3]
