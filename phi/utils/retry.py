import time
import random
import logging
from functools import wraps
from typing import Type, Tuple, Callable, Any

logger = logging.getLogger(__name__)

def exponential_backoff(
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    max_retries: int = 5,
    base_delay: float = 1,
    max_delay: float = 60,
    factor: float = 2,
    jitter: bool = True
) -> Callable:
    """
    A decorator that implements exponential backoff for the decorated function.
    
    Args:
        exceptions: A tuple of exception classes to catch and retry on.
        max_retries: Maximum number of retries before giving up.
        base_delay: The base delay time in seconds.
        max_delay: The maximum delay time in seconds.
        factor: The multiplying factor for exponential backoff.
        jitter: Whether to add a small random delay to avoid synchronization.
    
    Returns:
        A decorator function.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            retries = 0
            while True:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    retries += 1
                    if retries > max_retries:
                        logger.error(f"Max retries ({max_retries}) exceeded. Last exception: {str(e)}")
                        raise
                    
                    delay = min(max_delay, (factor ** retries) * base_delay)
                    if jitter:
                        delay += random.uniform(0, 1)
                    
                    logger.warning(f"Attempt {retries}/{max_retries} failed. Retrying in {delay:.2f} seconds. Error: {str(e)}")
                    time.sleep(delay)
        return wrapper
    return decorator