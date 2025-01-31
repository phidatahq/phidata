import sys
from dataclasses import dataclass


def dataclass_safe(*args, **kwargs):
    """A dataclass decorator that conditionally applies slots=True for Python 3.10+."""
    if sys.version_info >= (3, 10):
        # For Python 3.10 and above, use slots=True in the decorator
        return dataclass(*args, **kwargs)
    else:
        # For Python versions below 3.10, remove slots=True and handle __slots__ manually
        slots = kwargs.pop("slots", False)
        cls = dataclass(*args, **kwargs)
        if slots:
            # Manually define __slots__ based on the dataclass fields
            cls.__slots__ = [field.name for field in cls.__dataclass_fields__.values()]
        return cls
