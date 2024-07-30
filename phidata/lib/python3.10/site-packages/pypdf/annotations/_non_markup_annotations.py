from typing import Any, Optional, Tuple, Union

from ..constants import AnnotationFlag
from ..generic._base import (
    BooleanObject,
    NameObject,
)
from ..generic._data_structures import DictionaryObject
from ..generic._rectangle import RectangleObject
from ._base import AnnotationDictionary

DEFAULT_ANNOTATION_FLAG = AnnotationFlag(0)


class Popup(AnnotationDictionary):
    def __init__(
        self,
        *,
        rect: Union[RectangleObject, Tuple[float, float, float, float]],
        parent: Optional[DictionaryObject] = None,
        open: bool = False,
        **kwargs: Any,
    ):
        super().__init__(**kwargs)
        self.update(
            {
                NameObject("/Subtype"): NameObject("/Popup"),
                NameObject("/Rect"): RectangleObject(rect),
                NameObject("/Open"): BooleanObject(open),
            }
        )
        if parent:
            # This needs to be an indirect object
            try:
                self[NameObject("/Parent")] = parent.indirect_reference
            except AttributeError:
                from .._utils import logger_warning

                logger_warning(
                    "Unregistered Parent object : No Parent field set",
                    __name__,
                )
