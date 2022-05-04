import time
import functools

from phidata.utils.log import logger


def timer(func):
    """Print the runtime of the decorated function
    https://realpython.com/primer-on-python-decorators/#timing-functions
    """

    @functools.wraps(func)
    def wrapper_timer(*args, **kwargs):
        start_time = time.perf_counter()  # 1
        value = func(*args, **kwargs)
        end_time = time.perf_counter()  # 2
        run_time = end_time - start_time  # 3
        logger.debug(f"Finished {func.__name__!r} in {run_time:.4f} secs")
        return value

    return wrapper_timer
