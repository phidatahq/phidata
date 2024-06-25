from abc import ABC

from ..constants import AnnotationFlag
from ..generic import NameObject, NumberObject
from ..generic._data_structures import DictionaryObject


class AnnotationDictionary(DictionaryObject, ABC):
    def __init__(self) -> None:
        from ..generic._base import NameObject

        # "rect" should not be added here as PolyLine can automatically set it
        self[NameObject("/Type")] = NameObject("/Annot")
        # The flags was NOT added to the constructor on purpose: We expect that
        #   most users don't want to change the default. If they want, they
        #   can use the property. The default is 0.

    @property
    def flags(self) -> AnnotationFlag:
        return self.get(NameObject("/F"), AnnotationFlag(0))

    @flags.setter
    def flags(self, value: AnnotationFlag) -> None:
        self[NameObject("/F")] = NumberObject(value)


NO_FLAGS = AnnotationFlag(0)
