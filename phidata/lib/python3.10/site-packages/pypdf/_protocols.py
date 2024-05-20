"""Helpers for working with PDF types."""

from abc import abstractmethod
from pathlib import Path
from typing import IO, Any, Dict, List, Optional, Tuple, Union

try:
    # Python 3.8+: https://peps.python.org/pep-0586
    from typing import Protocol
except ImportError:
    from typing_extensions import Protocol  # type: ignore[assignment]

from ._utils import StrByteType, StreamType


class PdfObjectProtocol(Protocol):
    indirect_reference: Any

    def clone(
        self,
        pdf_dest: Any,
        force_duplicate: bool = False,
        ignore_fields: Union[Tuple[str, ...], List[str], None] = (),
    ) -> Any:
        ...  # pragma: no cover

    def _reference_clone(self, clone: Any, pdf_dest: Any) -> Any:
        ...  # pragma: no cover

    def get_object(self) -> Optional["PdfObjectProtocol"]:
        ...  # pragma: no cover

    def hash_value(self) -> bytes:
        ...  # pragma: no cover

    def write_to_stream(
        self, stream: StreamType, encryption_key: Union[None, str, bytes] = None
    ) -> None:
        ...  # pragma: no cover


class XmpInformationProtocol(PdfObjectProtocol):
    pass


class PdfCommonDocProtocol(Protocol):
    @property
    def pdf_header(self) -> str:
        ...  # pragma: no cover

    @property
    def pages(self) -> List[Any]:
        ...  # pragma: no cover

    @property
    def root_object(self) -> PdfObjectProtocol:
        ...  # pragma: no cover

    def get_object(self, indirect_reference: Any) -> Optional[PdfObjectProtocol]:
        ...  # pragma: no cover

    @property
    def strict(self) -> bool:
        ...  # pragma: no cover


class PdfReaderProtocol(PdfCommonDocProtocol, Protocol):
    @property
    @abstractmethod
    def xref(self) -> Dict[int, Dict[int, Any]]:
        ...  # pragma: no cover

    @property
    @abstractmethod
    def trailer(self) -> Dict[str, Any]:
        ...  # pragma: no cover


class PdfWriterProtocol(PdfCommonDocProtocol, Protocol):
    _objects: List[Any]
    _id_translated: Dict[int, Dict[int, int]]

    @abstractmethod
    def write(self, stream: Union[Path, StrByteType]) -> Tuple[bool, IO[Any]]:
        ...  # pragma: no cover

    @abstractmethod
    def _add_object(self, obj: Any) -> Any:
        ...  # pragma: no cover
