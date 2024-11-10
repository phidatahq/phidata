from phi.agent import Agent
from phi.tools.airflow import AirflowToolkit

agent = Agent(
    tools=[AirflowToolkit(dags_dir="dags", save_dag=True, read_dag=True)], show_tool_calls=True, markdown=True
)


dag_content = """
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'example_dag',
    default_args=default_args,
    description='A simple example DAG',
    schedule_interval=timedelta(days=1),
)

def print_hello():
    print("Hello from Airflow!")

task = PythonOperator(
    task_id='hello_task',
    python_callable=print_hello,
    dag=dag,
)
"""

agent.run(f"Save this DAG file as 'example_dag.py': {dag_content}")


agent.run("Read the contents of 'example_dag.py'")
