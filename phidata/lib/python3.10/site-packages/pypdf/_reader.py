# Copyright (c) 2006, Mathieu Fenniak
# Copyright (c) 2007, Ashish Kulkarni <kulkarni.ashish@gmail.com>
#
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

import os
import re
from io import BytesIO, UnsupportedOperation
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Optional,
    Tuple,
    Union,
    cast,
)

from ._doc_common import PdfDocCommon, convert_to_int
from ._encryption import Encryption, PasswordType
from ._page import PageObject
from ._utils import (
    StrByteType,
    StreamType,
    b_,
    logger_warning,
    read_non_whitespace,
    read_previous_line,
    read_until_whitespace,
    skip_over_comment,
    skip_over_whitespace,
)
from .constants import TrailerKeys as TK
from .errors import (
    EmptyFileError,
    FileNotDecryptedError,
    PdfReadError,
    PdfStreamError,
    WrongPasswordError,
)
from .generic import (
    ArrayObject,
    ContentStream,
    DecodedStreamObject,
    DictionaryObject,
    EncodedStreamObject,
    IndirectObject,
    NameObject,
    NullObject,
    NumberObject,
    PdfObject,
    TextStringObject,
    read_object,
)
from .xmp import XmpInformation


class PdfReader(PdfDocCommon):
    """
    Initialize a PdfReader object.

    This operation can take some time, as the PDF stream's cross-reference
    tables are read into memory.

    Args:
        stream: A File object or an object that supports the standard read
            and seek methods similar to a File object. Could also be a
            string representing a path to a PDF file.
        strict: Determines whether user should be warned of all
            problems and also causes some correctable problems to be fatal.
            Defaults to ``False``.
        password: Decrypt PDF file at initialization. If the
            password is None, the file will not be decrypted.
            Defaults to ``None``.
    """

    def __init__(
        self,
        stream: Union[StrByteType, Path],
        strict: bool = False,
        password: Union[None, str, bytes] = None,
    ) -> None:
        self.strict = strict
        self.flattened_pages: Optional[List[PageObject]] = None
        #: Storage of parsed PDF objects.
        self.resolved_objects: Dict[Tuple[Any, Any], Optional[PdfObject]] = {}
        self.xref_index = 0
        self._page_id2num: Optional[
            Dict[Any, Any]
        ] = None  # map page indirect_reference number to Page Number
        if hasattr(stream, "mode") and "b" not in stream.mode:
            logger_warning(
                "PdfReader stream/file object is not in binary mode. "
                "It may not be read correctly.",
                __name__,
            )
        if isinstance(stream, (str, Path)):
            with open(stream, "rb") as fh:
                stream = BytesIO(fh.read())
        self.read(stream)
        self.stream = stream

        self._override_encryption = False
        self._encryption: Optional[Encryption] = None
        if self.is_encrypted:
            self._override_encryption = True
            # Some documents may not have a /ID, use two empty
            # byte strings instead. Solves
            # https://github.com/py-pdf/pypdf/issues/608
            id_entry = self.trailer.get(TK.ID)
            id1_entry = id_entry[0].get_object().original_bytes if id_entry else b""
            encrypt_entry = cast(
                DictionaryObject, self.trailer[TK.ENCRYPT].get_object()
            )
            self._encryption = Encryption.read(encrypt_entry, id1_entry)

            # try empty password if no password provided
            pwd = password if password is not None else b""
            if (
                self._encryption.verify(pwd) == PasswordType.NOT_DECRYPTED
                and password is not None
            ):
                # raise if password provided
                raise WrongPasswordError("Wrong password")
            self._override_encryption = False
        elif password is not None:
            raise PdfReadError("Not encrypted file")

    @property
    def root_object(self) -> DictionaryObject:
        """Provide access to "/Root". standardized with PdfWriter."""
        return cast(DictionaryObject, self.trailer[TK.ROOT].get_object())

    @property
    def _info(self) -> Optional[DictionaryObject]:
        """
        Provide access to "/Info". standardized with PdfWriter.

        Returns:
            /Info Dictionary ; None if the entry does not exists
        """
        info = self.trailer.get(TK.INFO, None)
        if info is None:
            return None
        else:
            info = info.get_object()
            if info is None:
                raise PdfReadError(
                    "Trailer not found or does not point to document information directory"
                )
            return cast(DictionaryObject, info)

    @property
    def _ID(self) -> Optional[ArrayObject]:
        """
        Provide access to "/ID". standardized with PdfWriter.

        Returns:
            /ID array ; None if the entry does not exists
        """
        id = self.trailer.get(TK.ID, None)
        return None if id is None else cast(ArrayObject, id.get_object())

    def _repr_mimebundle_(
        self,
        include: Union[None, Iterable[str]] = None,
        exclude: Union[None, Iterable[str]] = None,
    ) -> Dict[str, Any]:
        """
        Integration into Jupyter Notebooks.

        This method returns a dictionary that maps a mime-type to it's
        representation.

        See https://ipython.readthedocs.io/en/stable/config/integrating.html
        """
        self.stream.seek(0)
        pdf_data = self.stream.read()
        data = {
            "application/pdf": pdf_data,
        }

        if include is not None:
            # Filter representations based on include list
            data = {k: v for k, v in data.items() if k in include}

        if exclude is not None:
            # Remove representations based on exclude list
            data = {k: v for k, v in data.items() if k not in exclude}

        return data

    @property
    def pdf_header(self) -> str:
        """
        The first 8 bytes of the file.

        This is typically something like ``'%PDF-1.6'`` and can be used to
        detect if the file is actually a PDF file and which version it is.
        """
        # TODO: Make this return a bytes object for consistency
        #       but that needs a deprecation
        loc = self.stream.tell()
        self.stream.seek(0, 0)
        pdf_file_version = self.stream.read(8).decode("utf-8", "backslashreplace")
        self.stream.seek(loc, 0)  # return to where it was
        return pdf_file_version

    @property
    def xmp_metadata(self) -> Optional[XmpInformation]:
        """XMP (Extensible Metadata Platform) data."""
        try:
            self._override_encryption = True
            return cast(XmpInformation, self.root_object.xmp_metadata)
        finally:
            self._override_encryption = False

    def _get_page(self, page_number: int) -> PageObject:
        """
        Retrieve a page by number from this PDF file.

        Args:
            page_number: The page number to retrieve
                (pages begin at zero)

        Returns:
            A :class:`PageObject<pypdf._page.PageObject>` instance.
        """
        if self.flattened_pages is None:
            self._flatten()
        assert self.flattened_pages is not None, "hint for mypy"
        return self.flattened_pages[page_number]

    def _get_page_number_by_indirect(
        self, indirect_reference: Union[None, int, NullObject, IndirectObject]
    ) -> Optional[int]:
        """
        Generate _page_id2num.

        Args:
            indirect_reference:

        Returns:
            The page number or None
        """
        if self._page_id2num is None:
            self._page_id2num = {
                x.indirect_reference.idnum: i for i, x in enumerate(self.pages)  # type: ignore
            }

        if indirect_reference is None or isinstance(indirect_reference, NullObject):
            return None
        if isinstance(indirect_reference, int):
            idnum = indirect_reference
        else:
            idnum = indirect_reference.idnum
        assert self._page_id2num is not None, "hint for mypy"
        ret = self._page_id2num.get(idnum, None)
        return ret

    def _get_object_from_stream(
        self, indirect_reference: IndirectObject
    ) -> Union[int, PdfObject, str]:
        # indirect reference to object in object stream
        # read the entire object stream into memory
        stmnum, idx = self.xref_objStm[indirect_reference.idnum]
        obj_stm: EncodedStreamObject = IndirectObject(stmnum, 0, self).get_object()  # type: ignore
        # This is an xref to a stream, so its type better be a stream
        assert cast(str, obj_stm["/Type"]) == "/ObjStm"
        # /N is the number of indirect objects in the stream
        assert idx < obj_stm["/N"]
        stream_data = BytesIO(b_(obj_stm.get_data()))
        for i in range(obj_stm["/N"]):  # type: ignore
            read_non_whitespace(stream_data)
            stream_data.seek(-1, 1)
            objnum = NumberObject.read_from_stream(stream_data)
            read_non_whitespace(stream_data)
            stream_data.seek(-1, 1)
            offset = NumberObject.read_from_stream(stream_data)
            read_non_whitespace(stream_data)
            stream_data.seek(-1, 1)
            if objnum != indirect_reference.idnum:
                # We're only interested in one object
                continue
            if self.strict and idx != i:
                raise PdfReadError("Object is in wrong index.")
            stream_data.seek(int(obj_stm["/First"] + offset), 0)  # type: ignore

            # to cope with some case where the 'pointer' is on a white space
            read_non_whitespace(stream_data)
            stream_data.seek(-1, 1)

            try:
                obj = read_object(stream_data, self)
            except PdfStreamError as exc:
                # Stream object cannot be read. Normally, a critical error, but
                # Adobe Reader doesn't complain, so continue (in strict mode?)
                logger_warning(
                    f"Invalid stream (index {i}) within object "
                    f"{indirect_reference.idnum} {indirect_reference.generation}: "
                    f"{exc}",
                    __name__,
                )

                if self.strict:  # pragma: no cover
                    raise PdfReadError(
                        f"Cannot read object stream: {exc}"
                    )  # pragma: no cover
                # Replace with null. Hopefully it's nothing important.
                obj = NullObject()  # pragma: no cover
            return obj

        if self.strict:  # pragma: no cover
            raise PdfReadError(
                "This is a fatal error in strict mode."
            )  # pragma: no cover
        return NullObject()  # pragma: no cover

    def get_object(
        self, indirect_reference: Union[int, IndirectObject]
    ) -> Optional[PdfObject]:
        if isinstance(indirect_reference, int):
            indirect_reference = IndirectObject(indirect_reference, 0, self)
        retval = self.cache_get_indirect_object(
            indirect_reference.generation, indirect_reference.idnum
        )
        if retval is not None:
            return retval
        if (
            indirect_reference.generation == 0
            and indirect_reference.idnum in self.xref_objStm
        ):
            retval = self._get_object_from_stream(indirect_reference)  # type: ignore
        elif (
            indirect_reference.generation in self.xref
            and indirect_reference.idnum in self.xref[indirect_reference.generation]
        ):
            if self.xref_free_entry.get(indirect_reference.generation, {}).get(
                indirect_reference.idnum, False
            ):
                return NullObject()
            start = self.xref[indirect_reference.generation][indirect_reference.idnum]
            self.stream.seek(start, 0)
            try:
                idnum, generation = self.read_object_header(self.stream)
                if (
                    idnum != indirect_reference.idnum
                    or generation != indirect_reference.generation
                ):
                    raise PdfReadError("not matching, we parse the file for it")
            except Exception:
                if hasattr(self.stream, "getbuffer"):
                    buf = bytes(self.stream.getbuffer())
                else:
                    p = self.stream.tell()
                    self.stream.seek(0, 0)
                    buf = self.stream.read(-1)
                    self.stream.seek(p, 0)
                m = re.search(
                    rf"\s{indirect_reference.idnum}\s+{indirect_reference.generation}\s+obj".encode(),
                    buf,
                )
                if m is not None:
                    logger_warning(
                        f"Object ID {indirect_reference.idnum},{indirect_reference.generation} ref repaired",
                        __name__,
                    )
                    self.xref[indirect_reference.generation][
                        indirect_reference.idnum
                    ] = (m.start(0) + 1)
                    self.stream.seek(m.start(0) + 1)
                    idnum, generation = self.read_object_header(self.stream)
                else:
                    idnum = -1  # exception will be raised below
            if idnum != indirect_reference.idnum and self.xref_index:
                # Xref table probably had bad indexes due to not being zero-indexed
                if self.strict:
                    raise PdfReadError(
                        f"Expected object ID ({indirect_reference.idnum} {indirect_reference.generation}) "
                        f"does not match actual ({idnum} {generation}); "
                        "xref table not zero-indexed."
                    )
                # xref table is corrected in non-strict mode
            elif idnum != indirect_reference.idnum and self.strict:
                # some other problem
                raise PdfReadError(
                    f"Expected object ID ({indirect_reference.idnum} "
                    f"{indirect_reference.generation}) does not match actual "
                    f"({idnum} {generation})."
                )
            if self.strict:
                assert generation == indirect_reference.generation
            retval = read_object(self.stream, self)  # type: ignore

            # override encryption is used for the /Encrypt dictionary
            if not self._override_encryption and self._encryption is not None:
                # if we don't have the encryption key:
                if not self._encryption.is_decrypted():
                    raise FileNotDecryptedError("File has not been decrypted")
                # otherwise, decrypt here...
                retval = cast(PdfObject, retval)
                retval = self._encryption.decrypt_object(
                    retval, indirect_reference.idnum, indirect_reference.generation
                )
        else:
            if hasattr(self.stream, "getbuffer"):
                buf = bytes(self.stream.getbuffer())
            else:
                p = self.stream.tell()
                self.stream.seek(0, 0)
                buf = self.stream.read(-1)
                self.stream.seek(p, 0)
            m = re.search(
                rf"\s{indirect_reference.idnum}\s+{indirect_reference.generation}\s+obj".encode(),
                buf,
            )
            if m is not None:
                logger_warning(
                    f"Object {indirect_reference.idnum} {indirect_reference.generation} found",
                    __name__,
                )
                if indirect_reference.generation not in self.xref:
                    self.xref[indirect_reference.generation] = {}
                self.xref[indirect_reference.generation][indirect_reference.idnum] = (
                    m.start(0) + 1
                )
                self.stream.seek(m.end(0) + 1)
                skip_over_whitespace(self.stream)
                self.stream.seek(-1, 1)
                retval = read_object(self.stream, self)  # type: ignore

                # override encryption is used for the /Encrypt dictionary
                if not self._override_encryption and self._encryption is not None:
                    # if we don't have the encryption key:
                    if not self._encryption.is_decrypted():
                        raise FileNotDecryptedError("File has not been decrypted")
                    # otherwise, decrypt here...
                    retval = cast(PdfObject, retval)
                    retval = self._encryption.decrypt_object(
                        retval, indirect_reference.idnum, indirect_reference.generation
                    )
            else:
                logger_warning(
                    f"Object {indirect_reference.idnum} {indirect_reference.generation} not defined.",
                    __name__,
                )
                if self.strict:
                    raise PdfReadError("Could not find object.")
        self.cache_indirect_object(
            indirect_reference.generation, indirect_reference.idnum, retval
        )
        return retval

    def read_object_header(self, stream: StreamType) -> Tuple[int, int]:
        # Should never be necessary to read out whitespace, since the
        # cross-reference table should put us in the right spot to read the
        # object header.  In reality... some files have stupid cross reference
        # tables that are off by whitespace bytes.
        extra = False
        skip_over_comment(stream)
        extra |= skip_over_whitespace(stream)
        stream.seek(-1, 1)
        idnum = read_until_whitespace(stream)
        extra |= skip_over_whitespace(stream)
        stream.seek(-1, 1)
        generation = read_until_whitespace(stream)
        extra |= skip_over_whitespace(stream)
        stream.seek(-1, 1)

        # although it's not used, it might still be necessary to read
        _obj = stream.read(3)

        read_non_whitespace(stream)
        stream.seek(-1, 1)
        if extra and self.strict:
            logger_warning(
                f"Superfluous whitespace found in object header {idnum} {generation}",  # type: ignore
                __name__,
            )
        return int(idnum), int(generation)

    def cache_get_indirect_object(
        self, generation: int, idnum: int
    ) -> Optional[PdfObject]:
        return self.resolved_objects.get((generation, idnum))

    def cache_indirect_object(
        self, generation: int, idnum: int, obj: Optional[PdfObject]
    ) -> Optional[PdfObject]:
        if (generation, idnum) in self.resolved_objects:
            msg = f"Overwriting cache for {generation} {idnum}"
            if self.strict:
                raise PdfReadError(msg)
            logger_warning(msg, __name__)
        self.resolved_objects[(generation, idnum)] = obj
        if obj is not None:
            obj.indirect_reference = IndirectObject(idnum, generation, self)
        return obj

    def _replace_object(self, indirect: IndirectObject, obj: PdfObject) -> PdfObject:
        # function reserved for future dev
        if indirect.pdf != self:
            raise ValueError("Cannot update PdfReader with external object")
        if (indirect.generation, indirect.idnum) not in self.resolved_objects:
            raise ValueError("Cannot find referenced object")
        self.resolved_objects[(indirect.generation, indirect.idnum)] = obj
        obj.indirect_reference = indirect
        return obj

    def read(self, stream: StreamType) -> None:
        self._basic_validation(stream)
        self._find_eof_marker(stream)
        startxref = self._find_startxref_pos(stream)

        # check and eventually correct the startxref only in not strict
        xref_issue_nr = self._get_xref_issues(stream, startxref)
        if xref_issue_nr != 0:
            if self.strict and xref_issue_nr:
                raise PdfReadError("Broken xref table")
            logger_warning(f"incorrect startxref pointer({xref_issue_nr})", __name__)

        # read all cross reference tables and their trailers
        self._read_xref_tables_and_trailers(stream, startxref, xref_issue_nr)

        # if not zero-indexed, verify that the table is correct; change it if necessary
        if self.xref_index and not self.strict:
            loc = stream.tell()
            for gen, xref_entry in self.xref.items():
                if gen == 65535:
                    continue
                xref_k = sorted(
                    xref_entry.keys()
                )  # must ensure ascendant to prevent damage
                for id in xref_k:
                    stream.seek(xref_entry[id], 0)
                    try:
                        pid, _pgen = self.read_object_header(stream)
                    except ValueError:
                        self._rebuild_xref_table(stream)
                        break
                    if pid == id - self.xref_index:
                        # fixing index item per item is required for revised PDF.
                        self.xref[gen][pid] = self.xref[gen][id]
                        del self.xref[gen][id]
                    # if not, then either it's just plain wrong, or the
                    # non-zero-index is actually correct
            stream.seek(loc, 0)  # return to where it was

        # remove wrong objects (not pointing to correct structures) - cf #2326
        if not self.strict:
            loc = stream.tell()
            for gen, xref_entry in self.xref.items():
                if gen == 65535:
                    continue
                ids = list(xref_entry.keys())
                for id in ids:
                    stream.seek(xref_entry[id], 0)
                    try:
                        self.read_object_header(stream)
                    except ValueError:
                        logger_warning(
                            f"Ignoring wrong pointing object {id} {gen} (offset {xref_entry[id]})",
                            __name__,
                        )
                        del xref_entry[id]  # we can delete the id, we are parsing ids
            stream.seek(loc, 0)  # return to where it was

    def _basic_validation(self, stream: StreamType) -> None:
        """Ensure file is not empty. Read at most 5 bytes."""
        stream.seek(0, os.SEEK_SET)
        try:
            header_byte = stream.read(5)
        except UnicodeDecodeError:
            raise UnsupportedOperation("cannot read header")
        if header_byte == b"":
            raise EmptyFileError("Cannot read an empty file")
        elif header_byte != b"%PDF-":
            if self.strict:
                raise PdfReadError(
                    f"PDF starts with '{header_byte.decode('utf8')}', "
                    "but '%PDF-' expected"
                )
            else:
                logger_warning(f"invalid pdf header: {header_byte}", __name__)
        stream.seek(0, os.SEEK_END)

    def _find_eof_marker(self, stream: StreamType) -> None:
        """
        Jump to the %%EOF marker.

        According to the specs, the %%EOF marker should be at the very end of
        the file. Hence for standard-compliant PDF documents this function will
        read only the last part (DEFAULT_BUFFER_SIZE).
        """
        HEADER_SIZE = 8  # to parse whole file, Header is e.g. '%PDF-1.6'
        line = b""
        while line[:5] != b"%%EOF":
            if stream.tell() < HEADER_SIZE:
                if self.strict:
                    raise PdfReadError("EOF marker not found")
                else:
                    logger_warning("EOF marker not found", __name__)
            line = read_previous_line(stream)

    def _find_startxref_pos(self, stream: StreamType) -> int:
        """
        Find startxref entry - the location of the xref table.

        Args:
            stream:

        Returns:
            The bytes offset
        """
        line = read_previous_line(stream)
        try:
            startxref = int(line)
        except ValueError:
            # 'startxref' may be on the same line as the location
            if not line.startswith(b"startxref"):
                raise PdfReadError("startxref not found")
            startxref = int(line[9:].strip())
            logger_warning("startxref on same line as offset", __name__)
        else:
            line = read_previous_line(stream)
            if line[:9] != b"startxref":
                raise PdfReadError("startxref not found")
        return startxref

    def _read_standard_xref_table(self, stream: StreamType) -> None:
        # standard cross-reference table
        ref = stream.read(3)
        if ref != b"ref":
            raise PdfReadError("xref table read error")
        read_non_whitespace(stream)
        stream.seek(-1, 1)
        first_time = True  # check if the first time looking at the xref table
        while True:
            num = cast(int, read_object(stream, self))
            if first_time and num != 0:
                self.xref_index = num
                if self.strict:
                    logger_warning(
                        "Xref table not zero-indexed. ID numbers for objects will be corrected.",
                        __name__,
                    )
                    # if table not zero indexed, could be due to error from when PDF was created
                    # which will lead to mismatched indices later on, only warned and corrected if self.strict==True
            first_time = False
            read_non_whitespace(stream)
            stream.seek(-1, 1)
            size = cast(int, read_object(stream, self))
            if not isinstance(size, int):
                logger_warning(
                    "Invalid/Truncated xref table. Rebuilding it.",
                    __name__,
                )
                self._rebuild_xref_table(stream)
                stream.read()
                return
            read_non_whitespace(stream)
            stream.seek(-1, 1)
            cnt = 0
            while cnt < size:
                line = stream.read(20)

                # It's very clear in section 3.4.3 of the PDF spec
                # that all cross-reference table lines are a fixed
                # 20 bytes (as of PDF 1.7). However, some files have
                # 21-byte entries (or more) due to the use of \r\n
                # (CRLF) EOL's. Detect that case, and adjust the line
                # until it does not begin with a \r (CR) or \n (LF).
                while line[0] in b"\x0D\x0A":
                    stream.seek(-20 + 1, 1)
                    line = stream.read(20)

                # On the other hand, some malformed PDF files
                # use a single character EOL without a preceding
                # space.  Detect that case, and seek the stream
                # back one character.  (0-9 means we've bled into
                # the next xref entry, t means we've bled into the
                # text "trailer"):
                if line[-1] in b"0123456789t":
                    stream.seek(-1, 1)

                try:
                    offset_b, generation_b = line[:16].split(b" ")
                    entry_type_b = line[17:18]

                    offset, generation = int(offset_b), int(generation_b)
                except Exception:
                    # if something wrong occurred
                    if hasattr(stream, "getbuffer"):
                        buf = bytes(stream.getbuffer())
                    else:
                        p = stream.tell()
                        stream.seek(0, 0)
                        buf = stream.read(-1)
                        stream.seek(p)

                    f = re.search(f"{num}\\s+(\\d+)\\s+obj".encode(), buf)
                    if f is None:
                        logger_warning(
                            f"entry {num} in Xref table invalid; object not found",
                            __name__,
                        )
                        generation = 65535
                        offset = -1
                    else:
                        logger_warning(
                            f"entry {num} in Xref table invalid but object found",
                            __name__,
                        )
                        generation = int(f.group(1))
                        offset = f.start()

                if generation not in self.xref:
                    self.xref[generation] = {}
                    self.xref_free_entry[generation] = {}
                if num in self.xref[generation]:
                    # It really seems like we should allow the last
                    # xref table in the file to override previous
                    # ones. Since we read the file backwards, assume
                    # any existing key is already set correctly.
                    pass
                else:
                    if entry_type_b == b"n":
                        self.xref[generation][num] = offset
                    try:
                        self.xref_free_entry[generation][num] = entry_type_b == b"f"
                    except Exception:
                        pass
                    try:
                        self.xref_free_entry[65535][num] = entry_type_b == b"f"
                    except Exception:
                        pass
                cnt += 1
                num += 1
            read_non_whitespace(stream)
            stream.seek(-1, 1)
            trailer_tag = stream.read(7)
            if trailer_tag != b"trailer":
                # more xrefs!
                stream.seek(-7, 1)
            else:
                break

    def _read_xref_tables_and_trailers(
        self, stream: StreamType, startxref: Optional[int], xref_issue_nr: int
    ) -> None:
        self.xref: Dict[int, Dict[Any, Any]] = {}
        self.xref_free_entry: Dict[int, Dict[Any, Any]] = {}
        self.xref_objStm: Dict[int, Tuple[Any, Any]] = {}
        self.trailer = DictionaryObject()
        while startxref is not None:
            # load the xref table
            stream.seek(startxref, 0)
            x = stream.read(1)
            if x in b"\r\n":
                x = stream.read(1)
            if x == b"x":
                startxref = self._read_xref(stream)
            elif xref_issue_nr:
                try:
                    self._rebuild_xref_table(stream)
                    break
                except Exception:
                    xref_issue_nr = 0
            elif x.isdigit():
                try:
                    xrefstream = self._read_pdf15_xref_stream(stream)
                except Exception as e:
                    if TK.ROOT in self.trailer:
                        logger_warning(
                            f"Previous trailer can not be read {e.args}",
                            __name__,
                        )
                        break
                    else:
                        raise PdfReadError(f"trailer can not be read {e.args}")
                trailer_keys = TK.ROOT, TK.ENCRYPT, TK.INFO, TK.ID, TK.SIZE
                for key in trailer_keys:
                    if key in xrefstream and key not in self.trailer:
                        self.trailer[NameObject(key)] = xrefstream.raw_get(key)
                if "/XRefStm" in xrefstream:
                    p = stream.tell()
                    stream.seek(cast(int, xrefstream["/XRefStm"]) + 1, 0)
                    self._read_pdf15_xref_stream(stream)
                    stream.seek(p, 0)
                if "/Prev" in xrefstream:
                    startxref = cast(int, xrefstream["/Prev"])
                else:
                    break
            else:
                startxref = self._read_xref_other_error(stream, startxref)

    def _read_xref(self, stream: StreamType) -> Optional[int]:
        self._read_standard_xref_table(stream)
        if stream.read(1) == b"":
            return None
        stream.seek(-1, 1)
        read_non_whitespace(stream)
        stream.seek(-1, 1)
        new_trailer = cast(Dict[str, Any], read_object(stream, self))
        for key, value in new_trailer.items():
            if key not in self.trailer:
                self.trailer[key] = value
        if "/XRefStm" in new_trailer:
            p = stream.tell()
            stream.seek(cast(int, new_trailer["/XRefStm"]) + 1, 0)
            try:
                self._read_pdf15_xref_stream(stream)
            except Exception:
                logger_warning(
                    f"XRef object at {new_trailer['/XRefStm']} can not be read, some object may be missing",
                    __name__,
                )
            stream.seek(p, 0)
        if "/Prev" in new_trailer:
            startxref = new_trailer["/Prev"]
            return startxref
        else:
            return None

    def _read_xref_other_error(
        self, stream: StreamType, startxref: int
    ) -> Optional[int]:
        # some PDFs have /Prev=0 in the trailer, instead of no /Prev
        if startxref == 0:
            if self.strict:
                raise PdfReadError(
                    "/Prev=0 in the trailer (try opening with strict=False)"
                )
            logger_warning(
                "/Prev=0 in the trailer - assuming there is no previous xref table",
                __name__,
            )
            return None
        # bad xref character at startxref.  Let's see if we can find
        # the xref table nearby, as we've observed this error with an
        # off-by-one before.
        stream.seek(-11, 1)
        tmp = stream.read(20)
        xref_loc = tmp.find(b"xref")
        if xref_loc != -1:
            startxref -= 10 - xref_loc
            return startxref
        # No explicit xref table, try finding a cross-reference stream.
        stream.seek(startxref, 0)
        for look in range(25):  # value extended to cope with more linearized files
            if stream.read(1).isdigit():
                # This is not a standard PDF, consider adding a warning
                startxref += look
                return startxref
        # no xref table found at specified location
        if "/Root" in self.trailer and not self.strict:
            # if Root has been already found, just raise warning
            logger_warning("Invalid parent xref., rebuild xref", __name__)
            try:
                self._rebuild_xref_table(stream)
                return None
            except Exception:
                raise PdfReadError("can not rebuild xref")
        raise PdfReadError("Could not find xref table at specified location")

    def _read_pdf15_xref_stream(
        self, stream: StreamType
    ) -> Union[ContentStream, EncodedStreamObject, DecodedStreamObject]:
        # PDF 1.5+ Cross-Reference Stream
        stream.seek(-1, 1)
        idnum, generation = self.read_object_header(stream)
        xrefstream = cast(ContentStream, read_object(stream, self))
        assert cast(str, xrefstream["/Type"]) == "/XRef"
        self.cache_indirect_object(generation, idnum, xrefstream)
        stream_data = BytesIO(b_(xrefstream.get_data()))
        # Index pairs specify the subsections in the dictionary. If
        # none create one subsection that spans everything.
        idx_pairs = xrefstream.get("/Index", [0, xrefstream.get("/Size")])
        entry_sizes = cast(Dict[Any, Any], xrefstream.get("/W"))
        assert len(entry_sizes) >= 3
        if self.strict and len(entry_sizes) > 3:
            raise PdfReadError(f"Too many entry sizes: {entry_sizes}")

        def get_entry(i: int) -> Union[int, Tuple[int, ...]]:
            # Reads the correct number of bytes for each entry. See the
            # discussion of the W parameter in PDF spec table 17.
            if entry_sizes[i] > 0:
                d = stream_data.read(entry_sizes[i])
                return convert_to_int(d, entry_sizes[i])

            # PDF Spec Table 17: A value of zero for an element in the
            # W array indicates...the default value shall be used
            if i == 0:
                return 1  # First value defaults to 1
            else:
                return 0

        def used_before(num: int, generation: Union[int, Tuple[int, ...]]) -> bool:
            # We move backwards through the xrefs, don't replace any.
            return num in self.xref.get(generation, []) or num in self.xref_objStm  # type: ignore

        # Iterate through each subsection
        self._read_xref_subsections(idx_pairs, get_entry, used_before)
        return xrefstream

    @staticmethod
    def _get_xref_issues(stream: StreamType, startxref: int) -> int:
        """
        Return an int which indicates an issue. 0 means there is no issue.

        Args:
            stream:
            startxref:

        Returns:
            0 means no issue, other values represent specific issues.
        """
        stream.seek(startxref - 1, 0)  # -1 to check character before
        line = stream.read(1)
        if line == b"j":
            line = stream.read(1)
        if line not in b"\r\n \t":
            return 1
        line = stream.read(4)
        if line != b"xref":
            # not an xref so check if it is an XREF object
            line = b""
            while line in b"0123456789 \t":
                line = stream.read(1)
                if line == b"":
                    return 2
            line += stream.read(2)  # 1 char already read, +2 to check "obj"
            if line.lower() != b"obj":
                return 3
        return 0

    def _rebuild_xref_table(self, stream: StreamType) -> None:
        self.xref = {}
        stream.seek(0, 0)
        f_ = stream.read(-1)

        for m in re.finditer(rb"[\r\n \t][ \t]*(\d+)[ \t]+(\d+)[ \t]+obj", f_):
            idnum = int(m.group(1))
            generation = int(m.group(2))
            if generation not in self.xref:
                self.xref[generation] = {}
            self.xref[generation][idnum] = m.start(1)
        stream.seek(0, 0)
        for m in re.finditer(rb"[\r\n \t][ \t]*trailer[\r\n \t]*(<<)", f_):
            stream.seek(m.start(1), 0)
            new_trailer = cast(Dict[Any, Any], read_object(stream, self))
            # Here, we are parsing the file from start to end, the new data have to erase the existing.
            for key, value in list(new_trailer.items()):
                self.trailer[key] = value

    def _read_xref_subsections(
        self,
        idx_pairs: List[int],
        get_entry: Callable[[int], Union[int, Tuple[int, ...]]],
        used_before: Callable[[int, Union[int, Tuple[int, ...]]], bool],
    ) -> None:
        for start, size in self._pairs(idx_pairs):
            # The subsections must increase
            for num in range(start, start + size):
                # The first entry is the type
                xref_type = get_entry(0)
                # The rest of the elements depend on the xref_type
                if xref_type == 0:
                    # linked list of free objects
                    next_free_object = get_entry(1)  # noqa: F841
                    next_generation = get_entry(2)  # noqa: F841
                elif xref_type == 1:
                    # objects that are in use but are not compressed
                    byte_offset = get_entry(1)
                    generation = get_entry(2)
                    if generation not in self.xref:
                        self.xref[generation] = {}  # type: ignore
                    if not used_before(num, generation):
                        self.xref[generation][num] = byte_offset  # type: ignore
                elif xref_type == 2:
                    # compressed objects
                    objstr_num = get_entry(1)
                    obstr_idx = get_entry(2)
                    generation = 0  # PDF spec table 18, generation is 0
                    if not used_before(num, generation):
                        self.xref_objStm[num] = (objstr_num, obstr_idx)
                elif self.strict:
                    raise PdfReadError(f"Unknown xref type: {xref_type}")

    def _pairs(self, array: List[int]) -> Iterable[Tuple[int, int]]:
        i = 0
        while True:
            yield array[i], array[i + 1]
            i += 2
            if (i + 1) >= len(array):
                break

    def decrypt(self, password: Union[str, bytes]) -> PasswordType:
        """
        When using an encrypted / secured PDF file with the PDF Standard
        encryption handler, this function will allow the file to be decrypted.
        It checks the given password against the document's user password and
        owner password, and then stores the resulting decryption key if either
        password is correct.

        It does not matter which password was matched.  Both passwords provide
        the correct decryption key that will allow the document to be used with
        this library.

        Args:
            password: The password to match.

        Returns:
            An indicator if the document was decrypted and whether it was the
            owner password or the user password.
        """
        if not self._encryption:
            raise PdfReadError("Not encrypted file")
        # TODO: raise Exception for wrong password
        return self._encryption.verify(password)

    @property
    def is_encrypted(self) -> bool:
        """
        Read-only boolean property showing whether this PDF file is encrypted.

        Note that this property, if true, will remain true even after the
        :meth:`decrypt()<pypdf.PdfReader.decrypt>` method is called.
        """
        return TK.ENCRYPT in self.trailer

    def add_form_topname(self, name: str) -> Optional[DictionaryObject]:
        """
        Add a top level form that groups all form fields below it.

        Args:
            name: text string of the "/T" Attribute of the created object

        Returns:
            The created object. ``None`` means no object was created.
        """
        catalog = self.root_object

        if "/AcroForm" not in catalog or not isinstance(
            catalog["/AcroForm"], DictionaryObject
        ):
            return None
        acroform = cast(DictionaryObject, catalog[NameObject("/AcroForm")])
        if "/Fields" not in acroform:
            # TODO: :No error returns but may be extended for XFA Forms
            return None

        interim = DictionaryObject()
        interim[NameObject("/T")] = TextStringObject(name)
        interim[NameObject("/Kids")] = acroform[NameObject("/Fields")]
        self.cache_indirect_object(
            0,
            max([i for (g, i) in self.resolved_objects if g == 0]) + 1,
            interim,
        )
        arr = ArrayObject()
        arr.append(interim.indirect_reference)
        acroform[NameObject("/Fields")] = arr
        for o in cast(ArrayObject, interim["/Kids"]):
            obj = o.get_object()
            if "/Parent" in obj:
                logger_warning(
                    f"Top Level Form Field {obj.indirect_reference} have a non-expected parent",
                    __name__,
                )
            obj[NameObject("/Parent")] = interim.indirect_reference
        return interim

    def rename_form_topname(self, name: str) -> Optional[DictionaryObject]:
        """
        Rename top level form field that all form fields below it.

        Args:
            name: text string of the "/T" field of the created object

        Returns:
            The modified object. ``None`` means no object was modified.
        """
        catalog = self.root_object

        if "/AcroForm" not in catalog or not isinstance(
            catalog["/AcroForm"], DictionaryObject
        ):
            return None
        acroform = cast(DictionaryObject, catalog[NameObject("/AcroForm")])
        if "/Fields" not in acroform:
            return None

        interim = cast(
            DictionaryObject,
            cast(ArrayObject, acroform[NameObject("/Fields")])[0].get_object(),
        )
        interim[NameObject("/T")] = TextStringObject(name)
        return interim
