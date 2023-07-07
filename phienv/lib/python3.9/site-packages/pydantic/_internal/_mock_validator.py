from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from pydantic_core import SchemaValidator

from pydantic.errors import PydanticErrorCodes, PydanticUserError

if TYPE_CHECKING:
    from ..dataclasses import PydanticDataclass
    from ..main import BaseModel


class MockValidator:
    """Mocker for `pydantic_core.SchemaValidator` which just raises an error when one of its methods is accessed."""

    __slots__ = '_error_message', '_code', '_attempt_rebuild'

    def __init__(
        self,
        error_message: str,
        *,
        code: PydanticErrorCodes,
        attempt_rebuild: Callable[[], SchemaValidator | None] | None = None,
    ) -> None:
        """Attempt rebuild."""
        self._error_message = error_message
        self._code: PydanticErrorCodes = code
        self._attempt_rebuild = attempt_rebuild

    def __getattr__(self, item: str) -> None:
        __tracebackhide__ = True
        if self._attempt_rebuild:
            validator = self._attempt_rebuild()
            if validator is not None:
                return getattr(validator, item)

        # raise an AttributeError if `item` doesn't exist
        getattr(SchemaValidator, item)
        raise PydanticUserError(self._error_message, code=self._code)


def set_basemodel_mock_validator(cls: type[BaseModel], cls_name: str, undefined_name: str) -> None:
    undefined_type_error_message = (
        f'`{cls_name}` is not fully defined; you should define {undefined_name},'
        f' then call `{cls_name}.model_rebuild()`'
        f' before the first `{cls_name}` instance is created.'
    )

    def attempt_rebuild() -> SchemaValidator | None:
        if cls.model_rebuild(raise_errors=False, _parent_namespace_depth=5):
            return cls.__pydantic_validator__
        else:
            return None

    cls.__pydantic_validator__ = MockValidator(  # type: ignore[assignment]
        undefined_type_error_message, code='class-not-fully-defined', attempt_rebuild=attempt_rebuild
    )


def set_dataclass_mock_validator(cls: type[PydanticDataclass], cls_name: str, undefined_name: str) -> None:
    undefined_type_error_message = (
        f'`{cls_name}` is not fully defined; you should define {undefined_name},'
        f' then call `pydantic.dataclasses.rebuild_dataclass({cls_name})`'
        f' before the first `{cls_name}` instance is created.'
    )

    def attempt_rebuild() -> SchemaValidator | None:
        from ..dataclasses import rebuild_dataclass

        if rebuild_dataclass(cls, raise_errors=False, _parent_namespace_depth=5):
            return cls.__pydantic_validator__  # type: ignore
        else:
            return None

    cls.__pydantic_validator__ = MockValidator(  # type: ignore[assignment]
        undefined_type_error_message, code='class-not-fully-defined', attempt_rebuild=attempt_rebuild
    )
