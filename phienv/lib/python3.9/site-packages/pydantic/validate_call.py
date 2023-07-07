"""Decorators for validating function calls."""
from __future__ import annotations as _annotations

from typing import TYPE_CHECKING, Any, Callable, TypeVar, overload

from ._internal import _validate_call

__all__ = ('validate_call',)

if TYPE_CHECKING:
    from .config import ConfigDict

    AnyCallableT = TypeVar('AnyCallableT', bound=Callable[..., Any])


@overload
def validate_call(
    *, config: ConfigDict | None = None, validate_return: bool = False
) -> Callable[[AnyCallableT], AnyCallableT]:
    ...


@overload
def validate_call(__func: AnyCallableT) -> AnyCallableT:
    ...


def validate_call(
    __func: AnyCallableT | None = None,
    *,
    config: ConfigDict | None = None,
    validate_return: bool = False,
) -> AnyCallableT | Callable[[AnyCallableT], AnyCallableT]:
    """Returns a decorated version of the function that validates the arguments and, optionally, the return value.

    Args:
        __func: The function to be decorated.
        config: The configuration dictionary.
        validate_return: Whether to validate the return value.

    Returns:
        The decorated function.
    """

    def validate(function: AnyCallableT) -> AnyCallableT:
        return _validate_call.ValidateCallWrapper(function, config, validate_return)  # type: ignore

    if __func:
        return validate(__func)
    else:
        return validate
