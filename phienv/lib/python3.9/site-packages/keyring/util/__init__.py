import functools


def once(func):
    """
    Decorate func so it's only ever called the first time.

    This decorator can ensure that an expensive or non-idempotent function
    will not be expensive on subsequent calls and is idempotent.

    >>> func = once(lambda a: a+3)
    >>> func(3)
    6
    >>> func(9)
    6
    >>> func('12')
    6
    """

    def wrapper(*args, **kwargs):
        if not hasattr(func, 'always_returns'):
            func.always_returns = func(*args, **kwargs)
        return func.always_returns

    return functools.wraps(func)(wrapper)


def suppress_exceptions(callables, exceptions=Exception):
    """
    yield the results of calling each element of callables, suppressing
    any indicated exceptions.
    """
    for callable in callables:
        try:
            yield callable()
        except exceptions:
            pass
