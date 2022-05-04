from typing import Optional
from functools import wraps, partial

from phidata.task.python_task import PythonTask, PythonTaskType, PythonTaskDecoratorType
from phidata.utils.log import logger


def task(func: PythonTaskType) -> PythonTaskDecoratorType:
    """Converts a function into a PythonTask"""

    wraps(func)

    def decorator(
        *args,
        name: Optional[str] = None,
        task_id: Optional[str] = None,
        dag_id: Optional[str] = None,
        version: Optional[str] = None,
        enabled: bool = True,
        **kwargs,
    ) -> PythonTask:
        # logger.info(f"task func: {func}")
        # logger.info(f"task kwargs: {kwargs}")
        task_name = name or func.__name__
        try:
            # create a partial function that can be called by the PythonTask
            entrypoint = partial(func, *args, **kwargs)
            python_task = PythonTask(
                name=task_name,
                entrypoint=entrypoint,
                task_id=task_id,
                dag_id=dag_id,
                entrypoint_args=args,
                entrypoint_kwargs=kwargs,
                version=version,
                enabled=enabled,
            )
            return python_task
        except Exception as e:
            logger.error(f"Could not create task: {task_name}")
            logger.error(e)
            raise

    return decorator
