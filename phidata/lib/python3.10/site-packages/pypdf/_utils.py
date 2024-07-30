# Copyright (c) 2006, Mathieu Fenniak
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
# * Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
# * The name of the author may not be used to endorse or promote products
# derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

"""Utility functions for PDF library."""
__author__ = "Mathieu Fenniak"
__author_email__ = "biziqe@mathieu.fenniak.net"

import functools
import logging
import re
import sys
import warnings
from dataclasses import dataclass
from datetime import datetime, timezone
from io import DEFAULT_BUFFER_SIZE, BytesIO
from os import SEEK_CUR
from typing import (
    IO,
    Any,
    Dict,
    List,
    Optional,
    Pattern,
    Tuple,
    Union,
    cast,
    overload,
)

if sys.version_info[:2] >= (3, 10):
    # Python 3.10+: https://www.python.org/dev/peps/pep-0484/
    from typing import TypeAlias
else:
    from typing_extensions import TypeAlias

from .errors import (
    STREAM_TRUNCATED_PREMATURELY,
    DeprecationError,
    PdfStreamError,
)

TransformationMatrixType: TypeAlias = Tuple[
    Tuple[float, float, float], Tuple[float, float, float], Tuple[float, float, float]
]
CompressedTransformationMatrix: TypeAlias = Tuple[
    float, float, float, float, float, float
]

StreamType = IO[Any]
StrByteType = Union[str, StreamType]

DEPR_MSG_NO_REPLACEMENT = "{} is deprecated and will be removed in pypdf {}."
DEPR_MSG_NO_REPLACEMENT_HAPPENED = "{} is deprecated and was removed in pypdf {}."
DEPR_MSG = "{} is deprecated and will be removed in pypdf {}. Use {} instead."
DEPR_MSG_HAPPENED = "{} is deprecated and was removed in pypdf {}. Use {} instead."


def parse_iso8824_date(text: Optional[str]) -> Optional[datetime]:
    orgtext = text
    if text is None:
        return None
    if text[0].isdigit():
        text = "D:" + text
    if text.endswith(("Z", "z")):
        text += "0000"
    text = text.replace("z", "+").replace("Z", "+").replace("'", "")
    i = max(text.find("+"), text.find("-"))
    if i > 0 and i != len(text) - 5:
        text += "00"
    for f in (
        "D:%Y",
        "D:%Y%m",
        "D:%Y%m%d",
        "D:%Y%m%d%H",
        "D:%Y%m%d%H%M",
        "D:%Y%m%d%H%M%S",
        "D:%Y%m%d%H%M%S%z",
    ):
        try:
            d = datetime.strptime(text, f)  # noqa: DTZ007
        except ValueError:
            continue
        else:
            if text[-5:] == "+0000":
                d = d.replace(tzinfo=timezone.utc)
            return d
    raise ValueError(f"Can not convert date: {orgtext}")


def _get_max_pdf_version_header(header1: str, header2: str) -> str:
    versions = (
        "%PDF-1.3",
        "%PDF-1.4",
        "%PDF-1.5",
        "%PDF-1.6",
        "%PDF-1.7",
        "%PDF-2.0",
    )
    pdf_header_indices = []
    if header1 in versions:
        pdf_header_indices.append(versions.index(header1))
    if header2 in versions:
        pdf_header_indices.append(versions.index(header2))
    if len(pdf_header_indices) == 0:
        raise ValueError(f"neither {header1!r} nor {header2!r} are proper headers")
    return versions[max(pdf_header_indices)]


def read_until_whitespace(stream: StreamType, maxchars: Optional[int] = None) -> bytes:
    """
    Read non-whitespace characters and return them.

    Stops upon encountering whitespace or when maxchars is reached.

    Args:
        stream: The data stream from which was read.
        maxchars: The maximum number of bytes returned; by default unlimited.

    Returns:
        The data which was read.
    """
    txt = b""
    while True:
        tok = stream.read(1)
        if tok.isspace() or not tok:
            break
        txt += tok
        if len(txt) == maxchars:
            break
    return txt


def read_non_whitespace(stream: StreamType) -> bytes:
    """
    Find and read the next non-whitespace character (ignores whitespace).

    Args:
        stream: The data stream from which was read.

    Returns:
        The data which was read.
    """
    tok = stream.read(1)
    while tok in WHITESPACES:
        tok = stream.read(1)
    return tok


def skip_over_whitespace(stream: StreamType) -> bool:
    """
    Similar to read_non_whitespace, but return a boolean if more than one
    whitespace character was read.

    Args:
        stream: The data stream from which was read.

    Returns:
        True if more than one whitespace was skipped, otherwise return False.
    """
    tok = WHITESPACES[0]
    cnt = 0
    while tok in WHITESPACES:
        tok = stream.read(1)
        cnt += 1
    return cnt > 1


def check_if_whitespace_only(value: bytes) -> bool:
    """
    Check if the given value consists of whitespace characters only.

    Args:
        value: The bytes to check.

    Returns:
        True if the value only has whitespace characters, otherwise return False.
    """
    for index in range(len(value)):
        current = value[index : index + 1]
        if current not in WHITESPACES:
            return False
    return True


def skip_over_comment(stream: StreamType) -> None:
    tok = stream.read(1)
    stream.seek(-1, 1)
    if tok == b"%":
        while tok not in (b"\n", b"\r"):
            tok = stream.read(1)


def read_until_regex(stream: StreamType, regex: Pattern[bytes]) -> bytes:
    """
    Read until the regular expression pattern matched (ignore the match).
    Treats EOF on the underlying stream as the end of the token to be matched.

    Args:
        regex: re.Pattern

    Returns:
        The read bytes.
    """
    name = b""
    while True:
        tok = stream.read(16)
        if not tok:
            return name
        m = regex.search(name + tok)
        if m is not None:
            stream.seek(m.start() - (len(name) + len(tok)), 1)
            name = (name + tok)[: m.start()]
            break
        name += tok
    return name


def read_block_backwards(stream: StreamType, to_read: int) -> bytes:
    """
    Given a stream at position X, read a block of size to_read ending at position X.

    This changes the stream's position to the beginning of where the block was
    read.

    Args:
        stream:
        to_read:

    Returns:
        The data which was read.
    """
    if stream.tell() < to_read:
        raise PdfStreamError("Could not read malformed PDF file")
    # Seek to the start of the block we want to read.
    stream.seek(-to_read, SEEK_CUR)
    read = stream.read(to_read)
    # Seek to the start of the block we read after reading it.
    stream.seek(-to_read, SEEK_CUR)
    return read


def read_previous_line(stream: StreamType) -> bytes:
    """
    Given a byte stream with current position X, return the previous line.

    All characters between the first CR/LF byte found before X
    (or, the start of the file, if no such byte is found) and position X
    After this call, the stream will be positioned one byte after the
    first non-CRLF character found beyond the first CR/LF byte before X,
    or, if no such byte is found, at the beginning of the stream.

    Args:
        stream: StreamType:

    Returns:
        The data which was read.
    """
    line_content = []
    found_crlf = False
    if stream.tell() == 0:
        raise PdfStreamError(STREAM_TRUNCATED_PREMATURELY)
    while True:
        to_read = min(DEFAULT_BUFFER_SIZE, stream.tell())
        if to_read == 0:
            break
        # Read the block. After this, our stream will be one
        # beyond the initial position.
        block = read_block_backwards(stream, to_read)
        idx = len(block) - 1
        if not found_crlf:
            # We haven't found our first CR/LF yet.
            # Read off characters until we hit one.
            while idx >= 0 and block[idx] not in b"\r\n":
                idx -= 1
            if idx >= 0:
                found_crlf = True
        if found_crlf:
            # We found our first CR/LF already (on this block or
            # a previous one).
            # Our combined line is the remainder of the block
            # plus any previously read blocks.
            line_content.append(block[idx + 1 :])
            # Continue to read off any more CRLF characters.
            while idx >= 0 and block[idx] in b"\r\n":
                idx -= 1
        else:
            # Didn't find CR/LF yet - add this block to our
            # previously read blocks and continue.
            line_content.append(block)
        if idx >= 0:
            # We found the next non-CRLF character.
            # Set the stream position correctly, then break
            stream.seek(idx + 1, SEEK_CUR)
            break
    # Join all the blocks in the line (which are in reverse order)
    return b"".join(line_content[::-1])


def matrix_multiply(
    a: TransformationMatrixType, b: TransformationMatrixType
) -> TransformationMatrixType:
    return tuple(  # type: ignore[return-value]
        tuple(sum(float(i) * float(j) for i, j in zip(row, col)) for col in zip(*b))
        for row in a
    )


def mark_location(stream: StreamType) -> None:
    """Create text file showing current location in context."""
    # Mainly for debugging
    radius = 5000
    stream.seek(-radius, 1)
    with open("pypdf_pdfLocation.txt", "wb") as output_fh:
        output_fh.write(stream.read(radius))
        output_fh.write(b"HERE")
        output_fh.write(stream.read(radius))
    stream.seek(-radius, 1)


B_CACHE: Dict[Union[str, bytes], bytes] = {}


def b_(s: Union[str, bytes]) -> bytes:
    if isinstance(s, bytes):
        return s
    bc = B_CACHE
    if s in bc:
        return bc[s]
    try:
        r = s.encode("latin-1")
        if len(s) < 2:
            bc[s] = r
        return r
    except Exception:
        r = s.encode("utf-8")
        if len(s) < 2:
            bc[s] = r
        return r


def str_(b: Any) -> str:
    if isinstance(b, bytes):
        return b.decode("latin-1")
    else:
        return str(b)  # will return b.__str__() if defined


@overload
def ord_(b: str) -> int:
    ...


@overload
def ord_(b: bytes) -> bytes:
    ...


@overload
def ord_(b: int) -> int:
    ...


def ord_(b: Union[int, str, bytes]) -> Union[int, bytes]:
    if isinstance(b, str):
        return ord(b)
    return b


WHITESPACES = (b" ", b"\n", b"\r", b"\t", b"\x00")
WHITESPACES_AS_REGEXP = b"[ \n\r\t\x00]"


def paeth_predictor(left: int, up: int, up_left: int) -> int:
    p = left + up - up_left
    dist_left = abs(p - left)
    dist_up = abs(p - up)
    dist_up_left = abs(p - up_left)

    if dist_left <= dist_up and dist_left <= dist_up_left:
        return left
    elif dist_up <= dist_up_left:
        return up
    else:
        return up_left


def deprecate(msg: str, stacklevel: int = 3) -> None:
    warnings.warn(msg, DeprecationWarning, stacklevel=stacklevel)


def deprecation(msg: str) -> None:
    raise DeprecationError(msg)


def deprecate_with_replacement(old_name: str, new_name: str, removed_in: str) -> None:
    """Raise an exception that a feature will be removed, but has a replacement."""
    deprecate(DEPR_MSG.format(old_name, removed_in, new_name), 4)


def deprecation_with_replacement(old_name: str, new_name: str, removed_in: str) -> None:
    """Raise an exception that a feature was already removed, but has a replacement."""
    deprecation(DEPR_MSG_HAPPENED.format(old_name, removed_in, new_name))


def deprecate_no_replacement(name: str, removed_in: str) -> None:
    """Raise an exception that a feature will be removed without replacement."""
    deprecate(DEPR_MSG_NO_REPLACEMENT.format(name, removed_in), 4)


def deprecation_no_replacement(name: str, removed_in: str) -> None:
    """Raise an exception that a feature was already removed without replacement."""
    deprecation(DEPR_MSG_NO_REPLACEMENT_HAPPENED.format(name, removed_in))


def logger_error(msg: str, src: str) -> None:
    """
    Use this instead of logger.error directly.

    That allows people to overwrite it more easily.

    See the docs on when to use which:
    https://pypdf.readthedocs.io/en/latest/user/suppress-warnings.html
    """
    logging.getLogger(src).error(msg)


def logger_warning(msg: str, src: str) -> None:
    """
    Use this instead of logger.warning directly.

    That allows people to overwrite it more easily.

    ## Exception, warnings.warn, logger_warning
    - Exceptions should be used if the user should write code that deals with
      an error case, e.g. the PDF being completely broken.
    - warnings.warn should be used if the user needs to fix their code, e.g.
      DeprecationWarnings
    - logger_warning should be used if the user needs to know that an issue was
      handled by pypdf, e.g. a non-compliant PDF being read in a way that
      pypdf could apply a robustness fix to still read it. This applies mainly
      to strict=False mode.
    """
    logging.getLogger(src).warning(msg)


def rename_kwargs(
    func_name: str, kwargs: Dict[str, Any], aliases: Dict[str, str], fail: bool = False
) -> None:
    """
    Helper function to deprecate arguments.

    Args:
        func_name: Name of the function to be deprecated
        kwargs:
        aliases:
        fail:
    """
    for old_term, new_term in aliases.items():
        if old_term in kwargs:
            if fail:
                raise DeprecationError(
                    f"{old_term} is deprecated as an argument. Use {new_term} instead"
                )
            if new_term in kwargs:
                raise TypeError(
                    f"{func_name} received both {old_term} and {new_term} as "
                    f"an argument. {old_term} is deprecated. "
                    f"Use {new_term} instead."
                )
            kwargs[new_term] = kwargs.pop(old_term)
            warnings.warn(
                message=(
                    f"{old_term} is deprecated as an argument. Use {new_term} instead"
                ),
                category=DeprecationWarning,
            )


def _human_readable_bytes(bytes: int) -> str:
    if bytes < 10**3:
        return f"{bytes} Byte"
    elif bytes < 10**6:
        return f"{bytes / 10**3:.1f} kB"
    elif bytes < 10**9:
        return f"{bytes / 10**6:.1f} MB"
    else:
        return f"{bytes / 10**9:.1f} GB"


@dataclass
class File:
    from .generic import IndirectObject

    name: str
    data: bytes
    image: Optional[Any] = None  # optional ; direct image access
    indirect_reference: Optional[IndirectObject] = None  # optional ; link to PdfObject

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name}, data: {_human_readable_bytes(len(self.data))})"

    def __repr__(self) -> str:
        return self.__str__()[:-1] + f", hash: {hash(self.data)})"


@dataclass
class ImageFile(File):
    from .generic import IndirectObject

    image: Optional[Any] = None  # optional ; direct PIL image access
    indirect_reference: Optional[IndirectObject] = None  # optional ; link to PdfObject

    def replace(self, new_image: Any, **kwargs: Any) -> None:
        """
        Replace the Image with a new PIL image.

        Args:
            new_image (PIL.Image.Image): The new PIL image to replace the existing image.
            **kwargs: Additional keyword arguments to pass to `Image.Image.save()`.

        Raises:
            TypeError: If the image is inline or in a PdfReader.
            TypeError: If the image does not belong to a PdfWriter.
            TypeError: If `new_image` is not a PIL Image.

        Note:
            This method replaces the existing image with a new image.
            It is not allowed for inline images or images within a PdfReader.
            The `kwargs` parameter allows passing additional parameters
            to `Image.Image.save()`, such as quality.
        """
        from PIL import Image

        from ._reader import PdfReader

        # to prevent circular import
        from .filters import _xobj_to_image
        from .generic import DictionaryObject, PdfObject

        if self.indirect_reference is None:
            raise TypeError("Can not update an inline image")
        if not hasattr(self.indirect_reference.pdf, "_id_translated"):
            raise TypeError("Can not update an image not belonging to a PdfWriter")
        if not isinstance(new_image, Image.Image):
            raise TypeError("new_image shall be a PIL Image")
        b = BytesIO()
        new_image.save(b, "PDF", **kwargs)
        reader = PdfReader(b)
        assert reader.pages[0].images[0].indirect_reference is not None
        self.indirect_reference.pdf._objects[self.indirect_reference.idnum - 1] = (
            reader.pages[0].images[0].indirect_reference.get_object()
        )
        cast(
            PdfObject, self.indirect_reference.get_object()
        ).indirect_reference = self.indirect_reference
        # change the object attributes
        extension, byte_stream, img = _xobj_to_image(
            cast(DictionaryObject, self.indirect_reference.get_object())
        )
        assert extension is not None
        self.name = self.name[: self.name.rfind(".")] + extension
        self.data = byte_stream
        self.image = img


@functools.total_ordering
class Version:
    COMPONENT_PATTERN = re.compile(r"^(\d+)(.*)$")

    def __init__(self, version_str: str) -> None:
        self.version_str = version_str
        self.components = self._parse_version(version_str)

    def _parse_version(self, version_str: str) -> List[Tuple[int, str]]:
        components = version_str.split(".")
        parsed_components = []
        for component in components:
            match = Version.COMPONENT_PATTERN.match(component)
            if not match:
                parsed_components.append((0, component))
                continue
            integer_prefix = match.group(1)
            suffix = match.group(2)
            if integer_prefix is None:
                integer_prefix = 0
            parsed_components.append((int(integer_prefix), suffix))
        return parsed_components

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Version):
            return False
        return self.components == other.components

    def __lt__(self, other: Any) -> bool:
        if not isinstance(other, Version):
            raise ValueError(f"Version cannot be compared against {type(other)}")
        min_len = min(len(self.components), len(other.components))
        for i in range(min_len):
            self_value, self_suffix = self.components[i]
            other_value, other_suffix = other.components[i]

            if self_value < other_value:
                return True
            elif self_value > other_value:
                return False

            if self_suffix < other_suffix:
                return True
            elif self_suffix > other_suffix:
                return False

        return len(self.components) < len(other.components)
