from functools import wraps, partial

from phi.task.py.python_task import PythonTask
from phi.utils.log import logger


def task(*args, **kwargs):
    # If the decorator was used without parentheses (e.g., @task)
    if args and callable(args[0]) and not kwargs:
        func = args[0]

        @wraps(func)
        def wrapper(*func_args, **func_kwargs):
            try:
                name = func.__name__
                entrypoint = partial(func, *func_args, **func_kwargs)
                python_task = PythonTask(name=name, entrypoint=entrypoint)
                return python_task
            except Exception as e:
                logger.error(f"Could not create task: {func.__name__}")
                logger.error(e)
                raise

        return wrapper
    # If the decorator was used with parentheses (e.g., @task(arg1=val1))
    else:

        def decorator(func):
            @wraps(func)
            def wrapper(*func_args, **func_kwargs):
                try:
                    name = func.__name__
                    entrypoint = partial(func, *func_args, **func_kwargs)
                    python_task = PythonTask(name=name, entrypoint=entrypoint, **kwargs)
                    return python_task
                except Exception as e:
                    logger.error(f"Could not create task: {func.__name__}")
                    logger.error(e)
                    raise

            return wrapper

        return decorator
