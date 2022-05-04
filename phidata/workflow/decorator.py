from typing import Optional, Callable
from functools import wraps, partial

from phidata.task.python_task import PythonTask, PythonTaskType
from phidata.workflow import Workflow
from phidata.utils.log import logger


def workflow(func: PythonTaskType) -> Callable[..., Workflow]:
    """Converts a function into a python workflow"""

    wraps(func)

    def decorator(
        *args,
        name: Optional[str] = None,
        task_id: Optional[str] = None,
        dag_id: Optional[str] = None,
        # create_db_engine_from_conn_id: bool = True,
        version: Optional[str] = None,
        enabled: bool = True,
        **kwargs,
    ) -> Workflow:
        # logger.info(f"workflow func: {func}")
        # logger.info(f"workflow kwargs: {kwargs}")
        task_name = name or func.__name__
        try:
            # create a partial function that can be called by the PythonTask
            entrypoint = partial(func, *args, **kwargs)
            python_task = PythonTask(
                name=task_name,
                entrypoint=entrypoint,
                task_id=task_id,
                dag_id=dag_id,
                # create_db_engine_from_conn_id=create_db_engine_from_conn_id,
                entrypoint_args=args,
                entrypoint_kwargs=kwargs,
                version=version,
                enabled=enabled,
            )
            python_wf = Workflow(
                name=task_name,
                tasks=[python_task],
                dag_id=dag_id,
            )
            return python_wf
        except Exception as e:
            logger.error(f"Could not create workflow: {task_name}")
            logger.error(e)
            raise

    return decorator


"""
@workflow
def simple_workflow(**kwargs) -> bool:
    logger.info(f"simple_workflow kwargs: {kwargs}")
    return True


sw = simple_workflow()
"""
