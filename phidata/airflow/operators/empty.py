from airflow.models.baseoperator import BaseOperator
from airflow.utils.context import Context


class EmptyOperator(BaseOperator):
    """
    Operator that does literally nothing. It can be used to group tasks in a
    DAG.
    The task is evaluated by the scheduler but never processed by the executor.

    # https://github.com/apache/airflow/blob/main/airflow/operators/empty.py
    # Note: use airflow.operators.empty.EmptyOperator when ^ is merged
    """

    ui_color = "#e8f7e4"
    inherits_from_empty_operator = True

    def execute(self, context: Context):
        pass
