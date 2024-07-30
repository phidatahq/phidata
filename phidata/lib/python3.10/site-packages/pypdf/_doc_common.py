# Copyright (c) 2006, Mathieu Fenniak
# Copyright (c) 2007, Ashish Kulkarni <kulkarni.ashish@gmail.com>
# Copyright (c) 2024, Pubpub-ZZ
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

import struct
import zlib
from abc import abstractmethod
from datetime import datetime
from typing import (
    Any,
    Dict,
    Iterable,
    Iterator,
    List,
    Mapping,
    Optional,
    Tuple,
    Union,
    cast,
)

from ._encryption import Encryption
from ._page import PageObject, _VirtualList
from ._page_labels import index2label as page_index2page_label
from ._utils import (
    b_,
    deprecate_with_replacement,
    logger_warning,
    parse_iso8824_date,
)
from .constants import CatalogAttributes as CA
from .constants import CatalogDictionary as CD
from .constants import (
    CheckboxRadioButtonAttributes,
    GoToActionArguments,
    UserAccessPermissions,
)
from .constants import Core as CO
from .constants import DocumentInformationAttributes as DI
from .constants import FieldDictionaryAttributes as FA
from .constants import PageAttributes as PG
from .constants import PagesAttributes as PA
from .errors import (
    PdfReadError,
)
from .generic import (
    ArrayObject,
    BooleanObject,
    ByteStringObject,
    Destination,
    DictionaryObject,
    EncodedStreamObject,
    Field,
    Fit,
    FloatObject,
    IndirectObject,
    NameObject,
    NullObject,
    NumberObject,
    PdfObject,
    TextStringObject,
    TreeObject,
    ViewerPreferences,
    create_string_object,
)
from .types import OutlineType, PagemodeType
from .xmp import XmpInformation


def convert_to_int(d: bytes, size: int) -> Union[int, Tuple[Any, ...]]:
    if size > 8:
        raise PdfReadError("invalid size in convert_to_int")
    d = b"\x00\x00\x00\x00\x00\x00\x00\x00" + d
    d = d[-8:]
    return struct.unpack(">q", d)[0]


class DocumentInformation(DictionaryObject):
    """
    A class representing the basic document metadata provided in a PDF File.
    This class is accessible through
    :py:class:`PdfReader.metadata<pypdf.PdfReader.metadata>`.

    All text properties of the document metadata have
    *two* properties, eg. author and author_raw. The non-raw property will
    always return a ``TextStringObject``, making it ideal for a case where
    the metadata is being displayed. The raw property can sometimes return
    a ``ByteStringObject``, if pypdf was unable to decode the string's
    text encoding; this requires additional safety in the caller and
    therefore is not as commonly accessed.
    """

    def __init__(self) -> None:
        DictionaryObject.__init__(self)

    def _get_text(self, key: str) -> Optional[str]:
        retval = self.get(key, None)
        if isinstance(retval, TextStringObject):
            return retval
        return None

    @property
    def title(self) -> Optional[str]:
        """
        Read-only property accessing the document's title.

        Returns a ``TextStringObject`` or ``None`` if the title is not
        specified.
        """
        return (
            self._get_text(DI.TITLE) or self.get(DI.TITLE).get_object()  # type: ignore
            if self.get(DI.TITLE)
            else None
        )

    @property
    def title_raw(self) -> Optional[str]:
        """The "raw" version of title; can return a ``ByteStringObject``."""
        return self.get(DI.TITLE)

    @property
    def author(self) -> Optional[str]:
        """
        Read-only property accessing the document's author.

        Returns a ``TextStringObject`` or ``None`` if the author is not
        specified.
        """
        return self._get_text(DI.AUTHOR)

    @property
    def author_raw(self) -> Optional[str]:
        """The "raw" version of author; can return a ``ByteStringObject``."""
        return self.get(DI.AUTHOR)

    @property
    def subject(self) -> Optional[str]:
        """
        Read-only property accessing the document's subject.

        Returns a ``TextStringObject`` or ``None`` if the subject is not
        specified.
        """
        return self._get_text(DI.SUBJECT)

    @property
    def subject_raw(self) -> Optional[str]:
        """The "raw" version of subject; can return a ``ByteStringObject``."""
        return self.get(DI.SUBJECT)

    @property
    def creator(self) -> Optional[str]:
        """
        Read-only property accessing the document's creator.

        If the document was converted to PDF from another format, this is the
        name of the application (e.g. OpenOffice) that created the original
        document from which it was converted. Returns a ``TextStringObject`` or
        ``None`` if the creator is not specified.
        """
        return self._get_text(DI.CREATOR)

    @property
    def creator_raw(self) -> Optional[str]:
        """The "raw" version of creator; can return a ``ByteStringObject``."""
        return self.get(DI.CREATOR)

    @property
    def producer(self) -> Optional[str]:
        """
        Read-only property accessing the document's producer.

        If the document was converted to PDF from another format, this is the
        name of the application (for example, macOS Quartz) that converted it to
        PDF. Returns a ``TextStringObject`` or ``None`` if the producer is not
        specified.
        """
        return self._get_text(DI.PRODUCER)

    @property
    def producer_raw(self) -> Optional[str]:
        """The "raw" version of producer; can return a ``ByteStringObject``."""
        return self.get(DI.PRODUCER)

    @property
    def creation_date(self) -> Optional[datetime]:
        """Read-only property accessing the document's creation date."""
        return parse_iso8824_date(self._get_text(DI.CREATION_DATE))

    @property
    def creation_date_raw(self) -> Optional[str]:
        """
        The "raw" version of creation date; can return a ``ByteStringObject``.

        Typically in the format ``D:YYYYMMDDhhmmss[+Z-]hh'mm`` where the suffix
        is the offset from UTC.
        """
        return self.get(DI.CREATION_DATE)

    @property
    def modification_date(self) -> Optional[datetime]:
        """
        Read-only property accessing the document's modification date.

        The date and time the document was most recently modified.
        """
        return parse_iso8824_date(self._get_text(DI.MOD_DATE))

    @property
    def modification_date_raw(self) -> Optional[str]:
        """
        The "raw" version of modification date; can return a
        ``ByteStringObject``.

        Typically in the format ``D:YYYYMMDDhhmmss[+Z-]hh'mm`` where the suffix
        is the offset from UTC.
        """
        return self.get(DI.MOD_DATE)


class PdfDocCommon:
    """
    Common functions from PdfWriter and PdfReader objects.

    This root class is strongly abstracted.
    """

    strict: bool = False  # default

    _encryption: Optional[Encryption] = None

    @property
    @abstractmethod
    def root_object(self) -> DictionaryObject:
        ...  # pragma: no cover

    @property
    @abstractmethod
    def pdf_header(self) -> str:
        ...  # pragma: no cover

    @abstractmethod
    def get_object(
        self, indirect_reference: Union[int, IndirectObject]
    ) -> Optional[PdfObject]:
        ...  # pragma: no cover

    @abstractmethod
    def _replace_object(self, indirect: IndirectObject, obj: PdfObject) -> PdfObject:
        ...  # pragma: no cover

    @property
    @abstractmethod
    def _info(self) -> Optional[DictionaryObject]:
        ...  # pragma: no cover

    @property
    def metadata(self) -> Optional[DocumentInformation]:
        """
        Retrieve the PDF file's document information dictionary, if it exists.

        Note that some PDF files use metadata streams instead of document
        information dictionaries, and these metadata streams will not be
        accessed by this function.
        """
        retval = DocumentInformation()
        if self._info is None:
            return None
        retval.update(self._info)
        return retval

    @property
    def xmp_metadata(self) -> Optional[XmpInformation]:
        ...  # pragma: no cover

    @abstractmethod
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
        ...  # pragma: no cover

    @property
    def viewer_preferences(self) -> Optional[ViewerPreferences]:
        """Returns the existing ViewerPreferences as an overloaded dictionary."""
        o = self.root_object.get(CD.VIEWER_PREFERENCES, None)
        if o is None:
            return None
        o = o.get_object()
        if not isinstance(o, ViewerPreferences):
            o = ViewerPreferences(o)
            if hasattr(o, "indirect_reference"):
                self._replace_object(o.indirect_reference, o)
            else:
                self.root_object[NameObject(CD.VIEWER_PREFERENCES)] = o
        return o

    flattened_pages: Optional[List[PageObject]] = None

    def get_num_pages(self) -> int:
        """
        Calculate the number of pages in this PDF file.

        Returns:
            The number of pages of the parsed PDF file

        Raises:
            PdfReadError: if file is encrypted and restrictions prevent
                this action.
        """
        # Flattened pages will not work on an encrypted PDF;
        # the PDF file's page count is used in this case. Otherwise,
        # the original method (flattened page count) is used.
        if self.is_encrypted:
            return self.root_object["/Pages"]["/Count"]  # type: ignore
        else:
            if self.flattened_pages is None:
                self._flatten()
            assert self.flattened_pages is not None
            return len(self.flattened_pages)

    def get_page(self, page_number: int) -> PageObject:
        """
        Retrieve a page by number from this PDF file.
        Most of the time ```.pages[page_number]``` is preferred.

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

    @property
    def named_destinations(self) -> Dict[str, Any]:
        """
        A read-only dictionary which maps names to
        :class:`Destinations<pypdf.generic.Destination>`
        """
        return self._get_named_destinations()

    def get_named_dest_root(self) -> ArrayObject:
        named_dest = ArrayObject()
        if CA.NAMES in self.root_object and isinstance(
            self.root_object[CA.NAMES], DictionaryObject
        ):
            names = cast(DictionaryObject, self.root_object[CA.NAMES])
            names_ref = names.indirect_reference
            if CA.DESTS in names and isinstance(names[CA.DESTS], DictionaryObject):
                # 3.6.3 Name Dictionary (PDF spec 1.7)
                dests = cast(DictionaryObject, names[CA.DESTS])
                dests_ref = dests.indirect_reference
                if CA.NAMES in dests:
                    # TABLE 3.33 Entries in a name tree node dictionary
                    named_dest = cast(ArrayObject, dests[CA.NAMES])
                else:
                    named_dest = ArrayObject()
                    dests[NameObject(CA.NAMES)] = named_dest
            elif hasattr(self, "_add_object"):
                dests = DictionaryObject()
                dests_ref = self._add_object(dests)
                names[NameObject(CA.DESTS)] = dests_ref
                dests[NameObject(CA.NAMES)] = named_dest

        elif hasattr(self, "_add_object"):
            names = DictionaryObject()
            names_ref = self._add_object(names)
            self.root_object[NameObject(CA.NAMES)] = names_ref
            dests = DictionaryObject()
            dests_ref = self._add_object(dests)
            names[NameObject(CA.DESTS)] = dests_ref
            dests[NameObject(CA.NAMES)] = named_dest

        return named_dest

    ## common
    def _get_named_destinations(
        self,
        tree: Union[TreeObject, None] = None,
        retval: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Retrieve the named destinations present in the document.

        Args:
            tree:
            retval:

        Returns:
            A dictionary which maps names to
            :class:`Destinations<pypdf.generic.Destination>`.
        """
        if retval is None:
            retval = {}
            catalog = self.root_object

            # get the name tree
            if CA.DESTS in catalog:
                tree = cast(TreeObject, catalog[CA.DESTS])
            elif CA.NAMES in catalog:
                names = cast(DictionaryObject, catalog[CA.NAMES])
                if CA.DESTS in names:
                    tree = cast(TreeObject, names[CA.DESTS])

        if tree is None:
            return retval

        if PA.KIDS in tree:
            # recurse down the tree
            for kid in cast(ArrayObject, tree[PA.KIDS]):
                self._get_named_destinations(kid.get_object(), retval)
        # TABLE 3.33 Entries in a name tree node dictionary (PDF 1.7 specs)
        elif CA.NAMES in tree:  # KIDS and NAMES are exclusives (PDF 1.7 specs p 162)
            names = cast(DictionaryObject, tree[CA.NAMES])
            i = 0
            while i < len(names):
                key = cast(str, names[i].get_object())
                i += 1
                if not isinstance(key, str):
                    continue
                try:
                    value = names[i].get_object()
                except IndexError:
                    break
                i += 1
                if isinstance(value, DictionaryObject):
                    if "/D" in value:
                        value = value["/D"]
                    else:
                        continue
                dest = self._build_destination(key, value)  # type: ignore
                if dest is not None:
                    retval[key] = dest
        else:  # case where Dests is in root catalog (PDF 1.7 specs, §2 about PDF 1.1)
            for k__, v__ in tree.items():
                val = v__.get_object()
                if isinstance(val, DictionaryObject):
                    if "/D" in val:
                        val = val["/D"].get_object()
                    else:
                        continue
                dest = self._build_destination(k__, val)
                if dest is not None:
                    retval[k__] = dest
        return retval

    # A select group of relevant field attributes. For the complete list.
    # See §12.3.2 of the PDF 1.7 or PDF 2.0 specification.

    def get_fields(
        self,
        tree: Optional[TreeObject] = None,
        retval: Optional[Dict[Any, Any]] = None,
        fileobj: Optional[Any] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Extract field data if this PDF contains interactive form fields.

        The *tree* and *retval* parameters are for recursive use.

        Args:
            tree:
            retval:
            fileobj: A file object (usually a text file) to write
                a report to on all interactive form fields found.

        Returns:
            A dictionary where each key is a field name, and each
            value is a :class:`Field<pypdf.generic.Field>` object. By
            default, the mapping name is used for keys.
            ``None`` if form data could not be located.
        """
        field_attributes = FA.attributes_dict()
        field_attributes.update(CheckboxRadioButtonAttributes.attributes_dict())
        if retval is None:
            retval = {}
            catalog = self.root_object
            # get the AcroForm tree
            if CD.ACRO_FORM in catalog:
                tree = cast(Optional[TreeObject], catalog[CD.ACRO_FORM])
            else:
                return None
        if tree is None:
            return retval
        self._check_kids(tree, retval, fileobj)
        for attr in field_attributes:
            if attr in tree:
                # Tree is a field
                self._build_field(tree, retval, fileobj, field_attributes)
                break

        if "/Fields" in tree:
            fields = cast(ArrayObject, tree["/Fields"])
            for f in fields:
                field = f.get_object()
                self._build_field(field, retval, fileobj, field_attributes)

        return retval

    def _get_qualified_field_name(self, parent: DictionaryObject) -> str:
        if "/TM" in parent:
            return cast(str, parent["/TM"])
        elif "/Parent" in parent:
            return (
                self._get_qualified_field_name(
                    cast(DictionaryObject, parent["/Parent"])
                )
                + "."
                + cast(str, parent.get("/T", ""))
            )
        else:
            return cast(str, parent.get("/T", ""))

    def _build_field(
        self,
        field: Union[TreeObject, DictionaryObject],
        retval: Dict[Any, Any],
        fileobj: Any,
        field_attributes: Any,
    ) -> None:
        self._check_kids(field, retval, fileobj)
        try:
            key = cast(str, field["/TM"])
        except KeyError:
            try:
                if "/Parent" in field:
                    key = (
                        self._get_qualified_field_name(
                            cast(DictionaryObject, field["/Parent"])
                        )
                        + "."
                    )
                else:
                    key = ""
                key += cast(str, field["/T"])
            except KeyError:
                # Ignore no-name field for now
                return
        if fileobj:
            self._write_field(fileobj, field, field_attributes)
            fileobj.write("\n")
        retval[key] = Field(field)
        obj = retval[key].indirect_reference.get_object()  # to get the full object
        if obj.get(FA.FT, "") == "/Ch":
            retval[key][NameObject("/_States_")] = obj[NameObject(FA.Opt)]
        if obj.get(FA.FT, "") == "/Btn" and "/AP" in obj:
            #  Checkbox
            retval[key][NameObject("/_States_")] = ArrayObject(
                list(obj["/AP"]["/N"].keys())
            )
            if "/Off" not in retval[key]["/_States_"]:
                retval[key][NameObject("/_States_")].append(NameObject("/Off"))
        elif obj.get(FA.FT, "") == "/Btn" and obj.get(FA.Ff, 0) & FA.FfBits.Radio != 0:
            states: List[str] = []
            retval[key][NameObject("/_States_")] = ArrayObject(states)
            for k in obj.get(FA.Kids, {}):
                k = k.get_object()
                for s in list(k["/AP"]["/N"].keys()):
                    if s not in states:
                        states.append(s)
                retval[key][NameObject("/_States_")] = ArrayObject(states)
            if (
                obj.get(FA.Ff, 0) & FA.FfBits.NoToggleToOff != 0
                and "/Off" in retval[key]["/_States_"]
            ):
                del retval[key]["/_States_"][retval[key]["/_States_"].index("/Off")]

    def _check_kids(
        self, tree: Union[TreeObject, DictionaryObject], retval: Any, fileobj: Any
    ) -> None:
        if PA.KIDS in tree:
            # recurse down the tree
            for kid in tree[PA.KIDS]:  # type: ignore
                self.get_fields(kid.get_object(), retval, fileobj)

    def _write_field(self, fileobj: Any, field: Any, field_attributes: Any) -> None:
        field_attributes_tuple = FA.attributes()
        field_attributes_tuple = (
            field_attributes_tuple + CheckboxRadioButtonAttributes.attributes()
        )

        for attr in field_attributes_tuple:
            if attr in (
                FA.Kids,
                FA.AA,
            ):
                continue
            attr_name = field_attributes[attr]
            try:
                if attr == FA.FT:
                    # Make the field type value more clear
                    types = {
                        "/Btn": "Button",
                        "/Tx": "Text",
                        "/Ch": "Choice",
                        "/Sig": "Signature",
                    }
                    if field[attr] in types:
                        fileobj.write(f"{attr_name}: {types[field[attr]]}\n")
                elif attr == FA.Parent:
                    # Let's just write the name of the parent
                    try:
                        name = field[attr][FA.TM]
                    except KeyError:
                        name = field[attr][FA.T]
                    fileobj.write(f"{attr_name}: {name}\n")
                else:
                    fileobj.write(f"{attr_name}: {field[attr]}\n")
            except KeyError:
                # Field attribute is N/A or unknown, so don't write anything
                pass

    def get_form_text_fields(self, full_qualified_name: bool = False) -> Dict[str, Any]:
        """
        Retrieve form fields from the document with textual data.

        Args:
            full_qualified_name: to get full name

        Returns:
            A dictionary. The key is the name of the form field,
            the value is the content of the field.

            If the document contains multiple form fields with the same name, the
            second and following will get the suffix .2, .3, ...
        """

        def indexed_key(k: str, fields: Dict[Any, Any]) -> str:
            if k not in fields:
                return k
            else:
                return (
                    k
                    + "."
                    + str(sum([1 for kk in fields if kk.startswith(k + ".")]) + 2)
                )

        # Retrieve document form fields
        formfields = self.get_fields()
        if formfields is None:
            return {}
        ff = {}
        for field, value in formfields.items():
            if value.get("/FT") == "/Tx":
                if full_qualified_name:
                    ff[field] = value.get("/V")
                else:
                    ff[indexed_key(cast(str, value["/T"]), ff)] = value.get("/V")
        return ff

    def get_pages_showing_field(
        self, field: Union[Field, PdfObject, IndirectObject]
    ) -> List[PageObject]:
        """
        Provides list of pages where the field is called.

        Args:
            field: Field Object, PdfObject or IndirectObject referencing a Field

        Returns:
            List of pages:
                - Empty list:
                    The field has no widgets attached
                    (either hidden field or ancestor field).
                - Single page list:
                    Page where the widget is present
                    (most common).
                - Multi-page list:
                    Field with multiple kids widgets
                    (example: radio buttons, field repeated on multiple pages).
        """

        def _get_inherited(obj: DictionaryObject, key: str) -> Any:
            if key in obj:
                return obj[key]
            elif "/Parent" in obj:
                return _get_inherited(
                    cast(DictionaryObject, obj["/Parent"].get_object()), key
                )
            else:
                return None

        try:
            # to cope with all types
            field = cast(DictionaryObject, field.indirect_reference.get_object())  # type: ignore
        except Exception as exc:
            raise ValueError("field type is invalid") from exc
        if _get_inherited(field, "/FT") is None:
            raise ValueError("field is not valid")
        ret = []
        if field.get("/Subtype", "") == "/Widget":
            if "/P" in field:
                ret = [field["/P"].get_object()]
            else:
                ret = [
                    p
                    for p in self.pages
                    if field.indirect_reference in p.get("/Annots", "")
                ]
        else:
            kids = field.get("/Kids", ())
            for k in kids:
                k = k.get_object()
                if (k.get("/Subtype", "") == "/Widget") and ("/T" not in k):
                    # Kid that is just a widget, not a field:
                    if "/P" in k:
                        ret += [k["/P"].get_object()]
                    else:
                        ret += [
                            p
                            for p in self.pages
                            if k.indirect_reference in p.get("/Annots", "")
                        ]
        return [
            x
            if isinstance(x, PageObject)
            else (self.pages[self._get_page_number_by_indirect(x.indirect_reference)])  # type: ignore
            for x in ret
        ]

    @property
    def open_destination(
        self,
    ) -> Union[None, Destination, TextStringObject, ByteStringObject]:
        """
        Property to access the opening destination (``/OpenAction`` entry in
        the PDF catalog). It returns ``None`` if the entry does not exist is not
        set.

        Raises:
            Exception: If a destination is invalid.
        """
        if "/OpenAction" not in self.root_object:
            return None
        oa: Any = self.root_object["/OpenAction"]
        if isinstance(oa, bytes):  # pragma: no cover
            oa = oa.decode()
        if isinstance(oa, str):
            return create_string_object(oa)
        elif isinstance(oa, ArrayObject):
            try:
                page, typ = oa[0:2]
                array = oa[2:]
                fit = Fit(typ, tuple(array))
                return Destination("OpenAction", page, fit)
            except Exception as exc:
                raise Exception(f"Invalid Destination {oa}: {exc}")
        else:
            return None

    @open_destination.setter
    def open_destination(self, dest: Union[None, str, Destination, PageObject]) -> None:
        raise NotImplementedError("no setter for open_destination")

    @property
    def outline(self) -> OutlineType:
        """
        Read-only property for the outline present in the document.

        (i.e., a collection of 'outline items' which are also known as
        'bookmarks')
        """
        return self._get_outline()

    def _get_outline(
        self, node: Optional[DictionaryObject] = None, outline: Optional[Any] = None
    ) -> OutlineType:
        if outline is None:
            outline = []
            catalog = self.root_object

            # get the outline dictionary and named destinations
            if CO.OUTLINES in catalog:
                lines = cast(DictionaryObject, catalog[CO.OUTLINES])

                if isinstance(lines, NullObject):
                    return outline

                # TABLE 8.3 Entries in the outline dictionary
                if lines is not None and "/First" in lines:
                    node = cast(DictionaryObject, lines["/First"])
            self._namedDests = self._get_named_destinations()

        if node is None:
            return outline

        # see if there are any more outline items
        while True:
            outline_obj = self._build_outline_item(node)
            if outline_obj:
                outline.append(outline_obj)

            # check for sub-outline
            if "/First" in node:
                sub_outline: List[Any] = []
                self._get_outline(cast(DictionaryObject, node["/First"]), sub_outline)
                if sub_outline:
                    outline.append(sub_outline)

            if "/Next" not in node:
                break
            node = cast(DictionaryObject, node["/Next"])

        return outline

    @property
    def threads(self) -> Optional[ArrayObject]:
        """
        Read-only property for the list of threads.

        See §8.3.2 from PDF 1.7 spec.

        It's an array of dictionaries with "/F" and "/I" properties or
        None if there are no articles.
        """
        catalog = self.root_object
        if CO.THREADS in catalog:
            return cast("ArrayObject", catalog[CO.THREADS])
        else:
            return None

    @abstractmethod
    def _get_page_number_by_indirect(
        self, indirect_reference: Union[None, int, NullObject, IndirectObject]
    ) -> Optional[int]:
        ...  # pragma: no cover

    def get_page_number(self, page: PageObject) -> Optional[int]:
        """
        Retrieve page number of a given PageObject.

        Args:
            page: The page to get page number. Should be
                an instance of :class:`PageObject<pypdf._page.PageObject>`

        Returns:
            The page number or None if page is not found
        """
        return self._get_page_number_by_indirect(page.indirect_reference)

    def get_destination_page_number(self, destination: Destination) -> Optional[int]:
        """
        Retrieve page number of a given Destination object.

        Args:
            destination: The destination to get page number.

        Returns:
            The page number or None if page is not found
        """
        return self._get_page_number_by_indirect(destination.page)

    def _build_destination(
        self,
        title: str,
        array: Optional[
            List[
                Union[NumberObject, IndirectObject, None, NullObject, DictionaryObject]
            ]
        ],
    ) -> Destination:
        page, typ = None, None
        # handle outline items with missing or invalid destination
        if (
            isinstance(array, (NullObject, str))
            or (isinstance(array, ArrayObject) and len(array) == 0)
            or array is None
        ):
            page = NullObject()
            return Destination(title, page, Fit.fit())
        else:
            page, typ = array[0:2]  # type: ignore
            array = array[2:]
            try:
                return Destination(title, page, Fit(fit_type=typ, fit_args=array))  # type: ignore
            except PdfReadError:
                logger_warning(f"Unknown destination: {title} {array}", __name__)
                if self.strict:
                    raise
                # create a link to first Page
                tmp = self.pages[0].indirect_reference
                indirect_reference = NullObject() if tmp is None else tmp
                return Destination(title, indirect_reference, Fit.fit())  # type: ignore

    def _build_outline_item(self, node: DictionaryObject) -> Optional[Destination]:
        dest, title, outline_item = None, None, None

        # title required for valid outline
        # PDF Reference 1.7: TABLE 8.4 Entries in an outline item dictionary
        try:
            title = cast("str", node["/Title"])
        except KeyError:
            if self.strict:
                raise PdfReadError(f"Outline Entry Missing /Title attribute: {node!r}")
            title = ""

        if "/A" in node:
            # Action, PDFv1.7 Section 12.6 (only type GoTo supported)
            action = cast(DictionaryObject, node["/A"])
            action_type = cast(NameObject, action[GoToActionArguments.S])
            if action_type == "/GoTo":
                dest = action[GoToActionArguments.D]
        elif "/Dest" in node:
            # Destination, PDFv1.7 Section 12.3.2
            dest = node["/Dest"]
            # if array was referenced in another object, will be a dict w/ key "/D"
            if isinstance(dest, DictionaryObject) and "/D" in dest:
                dest = dest["/D"]

        if isinstance(dest, ArrayObject):
            outline_item = self._build_destination(title, dest)
        elif isinstance(dest, str):
            # named destination, addresses NameObject Issue #193
            # TODO : keep named destination instead of replacing it ?
            try:
                outline_item = self._build_destination(
                    title, self._namedDests[dest].dest_array
                )
            except KeyError:
                # named destination not found in Name Dict
                outline_item = self._build_destination(title, None)
        elif dest is None:
            # outline item not required to have destination or action
            # PDFv1.7 Table 153
            outline_item = self._build_destination(title, dest)
        else:
            if self.strict:
                raise PdfReadError(f"Unexpected destination {dest!r}")
            else:
                logger_warning(
                    f"Removed unexpected destination {dest!r} from destination",
                    __name__,
                )
            outline_item = self._build_destination(title, None)

        # if outline item created, add color, format, and child count if present
        if outline_item:
            if "/C" in node:
                # Color of outline item font in (R, G, B) with values ranging 0.0-1.0
                outline_item[NameObject("/C")] = ArrayObject(FloatObject(c) for c in node["/C"])  # type: ignore
            if "/F" in node:
                # specifies style characteristics bold and/or italic
                # with 1=italic, 2=bold, 3=both
                outline_item[NameObject("/F")] = node["/F"]
            if "/Count" in node:
                # absolute value = num. visible children
                # with positive = open/unfolded, negative = closed/folded
                outline_item[NameObject("/Count")] = node["/Count"]
            #  if count is 0 we will consider it as open ( in order to have always an is_open to simplify
            outline_item[NameObject("/%is_open%")] = BooleanObject(
                node.get("/Count", 0) >= 0
            )
        outline_item.node = node
        try:
            outline_item.indirect_reference = node.indirect_reference
        except AttributeError:
            pass
        return outline_item

    @property
    def pages(self) -> List[PageObject]:
        """
        Property that emulates a list of :class:`PageObject<pypdf._page.PageObject>`.
        this property allows to get a page or a range of pages.

        For PdfWriter Only:
        It provides also capability to remove a page/range of page from the list
        (through del operator)
        Note: only the page entry is removed. As the objects beneath can be used
        somewhere else.
        A solution to completely remove them - if they are not used anywhere -
        is to write to a buffer/temporary file and to load it into a new PdfWriter
        object afterwards.
        """
        return _VirtualList(self.get_num_pages, self.get_page)  # type: ignore

    @property
    def page_labels(self) -> List[str]:
        """
        A list of labels for the pages in this document.

        This property is read-only. The labels are in the order that the pages
        appear in the document.
        """
        return [page_index2page_label(self, i) for i in range(len(self.pages))]

    @property
    def page_layout(self) -> Optional[str]:
        """
        Get the page layout currently being used.

        .. list-table:: Valid ``layout`` values
           :widths: 50 200

           * - /NoLayout
             - Layout explicitly not specified
           * - /SinglePage
             - Show one page at a time
           * - /OneColumn
             - Show one column at a time
           * - /TwoColumnLeft
             - Show pages in two columns, odd-numbered pages on the left
           * - /TwoColumnRight
             - Show pages in two columns, odd-numbered pages on the right
           * - /TwoPageLeft
             - Show two pages at a time, odd-numbered pages on the left
           * - /TwoPageRight
             - Show two pages at a time, odd-numbered pages on the right
        """
        try:
            return cast(NameObject, self.root_object[CD.PAGE_LAYOUT])
        except KeyError:
            return None

    @property
    def page_mode(self) -> Optional[PagemodeType]:
        """
        Get the page mode currently being used.

        .. list-table:: Valid ``mode`` values
           :widths: 50 200

           * - /UseNone
             - Do not show outline or thumbnails panels
           * - /UseOutlines
             - Show outline (aka bookmarks) panel
           * - /UseThumbs
             - Show page thumbnails panel
           * - /FullScreen
             - Fullscreen view
           * - /UseOC
             - Show Optional Content Group (OCG) panel
           * - /UseAttachments
             - Show attachments panel
        """
        try:
            return self.root_object["/PageMode"]  # type: ignore
        except KeyError:
            return None

    def _flatten(
        self,
        pages: Union[None, DictionaryObject, PageObject] = None,
        inherit: Optional[Dict[str, Any]] = None,
        indirect_reference: Optional[IndirectObject] = None,
    ) -> None:
        inheritable_page_attributes = (
            NameObject(PG.RESOURCES),
            NameObject(PG.MEDIABOX),
            NameObject(PG.CROPBOX),
            NameObject(PG.ROTATE),
        )
        if inherit is None:
            inherit = {}
        if pages is None:
            # Fix issue 327: set flattened_pages attribute only for
            # decrypted file
            catalog = self.root_object
            pages = catalog["/Pages"].get_object()  # type: ignore
            assert isinstance(pages, DictionaryObject)
            self.flattened_pages = []

        if PA.TYPE in pages:
            t = cast(str, pages[PA.TYPE])
        # if pdf has no type, considered as a page if /Kids is missing
        elif PA.KIDS not in pages:
            t = "/Page"
        else:
            t = "/Pages"

        if t == "/Pages":
            for attr in inheritable_page_attributes:
                if attr in pages:
                    inherit[attr] = pages[attr]
            for page in cast(ArrayObject, pages[PA.KIDS]):
                addt = {}
                if isinstance(page, IndirectObject):
                    addt["indirect_reference"] = page
                obj = page.get_object()
                if obj:
                    # damaged file may have invalid child in /Pages
                    self._flatten(obj, inherit, **addt)
        elif t == "/Page":
            for attr_in, value in list(inherit.items()):
                # if the page has it's own value, it does not inherit the
                # parent's value:
                if attr_in not in pages:
                    pages[attr_in] = value
            page_obj = PageObject(self, indirect_reference)
            page_obj.update(pages)

            # TODO: Could flattened_pages be None at this point?
            self.flattened_pages.append(page_obj)  # type: ignore

    def remove_page(
        self,
        page: Union[int, PageObject, IndirectObject],
        clean: bool = False,
    ) -> None:
        """
        Remove page from pages list.

        Args:
            page: int / PageObject / IndirectObject
                PageObject : page to be removed. If the page appears many times
                only the first one will be removed

                IndirectObject: Reference to page to be removed

                int: Page number to be removed

            clean: replace PageObject with NullObject to prevent destination,
                annotation to reference a detached page
        """
        if self.flattened_pages is None:
            self._flatten()
        assert self.flattened_pages is not None
        if isinstance(page, IndirectObject):
            p = page.get_object()
            if not isinstance(p, PageObject):
                logger_warning("IndirectObject is not referencing a page", __name__)
                return
            page = p

        if not isinstance(page, int):
            try:
                page = self.flattened_pages.index(page)
            except ValueError:
                logger_warning("Cannot find page in pages", __name__)
                return
        if not (0 <= page < len(self.flattened_pages)):
            logger_warning("Page number is out of range", __name__)
            return

        ind = self.pages[page].indirect_reference
        del self.pages[page]
        if clean and ind is not None:
            self._replace_object(ind, NullObject())

    def _get_indirect_object(self, num: int, gen: int) -> Optional[PdfObject]:
        """
        Used to ease development.

        This is equivalent to generic.IndirectObject(num,gen,self).get_object()

        Args:
            num: The object number of the indirect object.
            gen: The generation number of the indirect object.

        Returns:
            A PdfObject
        """
        return IndirectObject(num, gen, self).get_object()

    def decode_permissions(
        self, permissions_code: int
    ) -> Dict[str, bool]:  # pragma: no cover
        """Take the permissions as an integer, return the allowed access."""
        deprecate_with_replacement(
            old_name="decode_permissions",
            new_name="user_access_permissions",
            removed_in="5.0.0",
        )

        permissions_mapping = {
            "print": UserAccessPermissions.PRINT,
            "modify": UserAccessPermissions.MODIFY,
            "copy": UserAccessPermissions.EXTRACT,
            "annotations": UserAccessPermissions.ADD_OR_MODIFY,
            "forms": UserAccessPermissions.FILL_FORM_FIELDS,
            # Do not fix typo, as part of official, but deprecated API.
            "accessability": UserAccessPermissions.EXTRACT_TEXT_AND_GRAPHICS,
            "assemble": UserAccessPermissions.ASSEMBLE_DOC,
            "print_high_quality": UserAccessPermissions.PRINT_TO_REPRESENTATION,
        }

        return {
            key: permissions_code & flag != 0
            for key, flag in permissions_mapping.items()
        }

    @property
    def user_access_permissions(self) -> Optional[UserAccessPermissions]:
        """Get the user access permissions for encrypted documents. Returns None if not encrypted."""
        if self._encryption is None:
            return None
        return UserAccessPermissions(self._encryption.P)

    @property
    @abstractmethod
    def is_encrypted(self) -> bool:
        """
        Read-only boolean property showing whether this PDF file is encrypted.

        Note that this property, if true, will remain true even after the
        :meth:`decrypt()<pypdf.PdfReader.decrypt>` method is called.
        """
        ...  # pragma: no cover

    @property
    def xfa(self) -> Optional[Dict[str, Any]]:
        tree: Optional[TreeObject] = None
        retval: Dict[str, Any] = {}
        catalog = self.root_object

        if "/AcroForm" not in catalog or not catalog["/AcroForm"]:
            return None

        tree = cast(TreeObject, catalog["/AcroForm"])

        if "/XFA" in tree:
            fields = cast(ArrayObject, tree["/XFA"])
            i = iter(fields)
            for f in i:
                tag = f
                f = next(i)
                if isinstance(f, IndirectObject):
                    field = cast(Optional[EncodedStreamObject], f.get_object())
                    if field:
                        es = zlib.decompress(b_(field._data))
                        retval[tag] = es
        return retval

    @property
    def attachments(self) -> Mapping[str, List[bytes]]:
        return LazyDict(
            {
                name: (self._get_attachment_list, name)
                for name in self._list_attachments()
            }
        )

    def _list_attachments(self) -> List[str]:
        """
        Retrieves the list of filenames of file attachments.

        Returns:
            list of filenames
        """
        catalog = self.root_object
        # From the catalog get the embedded file names
        try:
            filenames = cast(
                ArrayObject,
                cast(
                    DictionaryObject,
                    cast(DictionaryObject, catalog["/Names"])["/EmbeddedFiles"],
                )["/Names"],
            )
        except KeyError:
            return []
        attachments_names = [f for f in filenames if isinstance(f, str)]
        return attachments_names

    def _get_attachment_list(self, name: str) -> List[bytes]:
        out = self._get_attachments(name)[name]
        if isinstance(out, list):
            return out
        return [out]

    def _get_attachments(
        self, filename: Optional[str] = None
    ) -> Dict[str, Union[bytes, List[bytes]]]:
        """
        Retrieves all or selected file attachments of the PDF as a dictionary of file names
        and the file data as a bytestring.

        Args:
            filename: If filename is None, then a dictionary of all attachments
                will be returned, where the key is the filename and the value
                is the content. Otherwise, a dictionary with just a single key
                - the filename - and its content will be returned.

        Returns:
            dictionary of filename -> Union[bytestring or List[ByteString]]
            If the filename exists multiple times a list of the different versions will be provided.
        """
        catalog = self.root_object
        # From the catalog get the embedded file names
        try:
            filenames = cast(
                ArrayObject,
                cast(
                    DictionaryObject,
                    cast(DictionaryObject, catalog["/Names"])["/EmbeddedFiles"],
                )["/Names"],
            )
        except KeyError:
            return {}
        attachments: Dict[str, Union[bytes, List[bytes]]] = {}
        # Loop through attachments
        for i in range(len(filenames)):
            f = filenames[i]
            if isinstance(f, str):
                if filename is not None and f != filename:
                    continue
                name = f
                f_dict = filenames[i + 1].get_object()
                f_data = f_dict["/EF"]["/F"].get_data()
                if name in attachments:
                    if not isinstance(attachments[name], list):
                        attachments[name] = [attachments[name]]  # type:ignore
                    attachments[name].append(f_data)  # type:ignore
                else:
                    attachments[name] = f_data
        return attachments


class LazyDict(Mapping[Any, Any]):
    def __init__(self, *args: Any, **kw: Any) -> None:
        self._raw_dict = dict(*args, **kw)

    def __getitem__(self, key: str) -> Any:
        func, arg = self._raw_dict.__getitem__(key)
        return func(arg)

    def __iter__(self) -> Iterator[Any]:
        return iter(self._raw_dict)

    def __len__(self) -> int:
        return len(self._raw_dict)

    def __str__(self) -> str:
        return f"LazyDict(keys={list(self.keys())})"
