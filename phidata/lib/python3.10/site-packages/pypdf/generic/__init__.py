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

"""Implementation of generic PDF objects (dictionary, number, string, ...)."""
__author__ = "Mathieu Fenniak"
__author_email__ = "biziqe@mathieu.fenniak.net"

from typing import Dict, List, Optional, Tuple, Union

from .._utils import StreamType, deprecate_with_replacement
from ..constants import OutlineFontFlag
from ._base import (
    BooleanObject,
    ByteStringObject,
    FloatObject,
    IndirectObject,
    NameObject,
    NullObject,
    NumberObject,
    PdfObject,
    TextStringObject,
    encode_pdfdocencoding,
)
from ._data_structures import (
    ArrayObject,
    ContentStream,
    DecodedStreamObject,
    Destination,
    DictionaryObject,
    EncodedStreamObject,
    Field,
    StreamObject,
    TreeObject,
    read_object,
)
from ._fit import Fit
from ._outline import OutlineItem
from ._rectangle import RectangleObject
from ._utils import (
    create_string_object,
    decode_pdfdocencoding,
    hex_to_rgb,
    read_hex_string_from_stream,
    read_string_from_stream,
)
from ._viewerpref import ViewerPreferences


def readHexStringFromStream(
    stream: StreamType,
) -> Union["TextStringObject", "ByteStringObject"]:  # deprecated
    """Deprecated, use read_hex_string_from_stream."""
    deprecate_with_replacement(
        "readHexStringFromStream", "read_hex_string_from_stream", "4.0.0"
    )
    return read_hex_string_from_stream(stream)


def readStringFromStream(
    stream: StreamType,
    forced_encoding: Union[None, str, List[str], Dict[int, str]] = None,
) -> Union["TextStringObject", "ByteStringObject"]:  # deprecated
    """Deprecated, use read_string_from_stream."""
    deprecate_with_replacement(
        "readStringFromStream", "read_string_from_stream", "4.0.0"
    )
    return read_string_from_stream(stream, forced_encoding)


def createStringObject(
    string: Union[str, bytes],
    forced_encoding: Union[None, str, List[str], Dict[int, str]] = None,
) -> Union[TextStringObject, ByteStringObject]:  # deprecated
    """Deprecated, use create_string_object."""
    deprecate_with_replacement("createStringObject", "create_string_object", "4.0.0")
    return create_string_object(string, forced_encoding)


PAGE_FIT = Fit.fit()


class AnnotationBuilder:
    """
    The AnnotationBuilder is deprecated.

    Instead, use the annotation classes in pypdf.annotations.

    See `adding PDF annotations <../user/adding-pdf-annotations.html>`_ for
    it's usage combined with PdfWriter.
    """

    from ..generic._rectangle import RectangleObject

    @staticmethod
    def text(
        rect: Union[RectangleObject, Tuple[float, float, float, float]],
        text: str,
        open: bool = False,
        flags: int = 0,
    ) -> DictionaryObject:
        """
        Add text annotation.

        Args:
            rect: array of four integers ``[xLL, yLL, xUR, yUR]``
                specifying the clickable rectangular area
            text: The text that is added to the document
            open:
            flags:

        Returns:
            A dictionary object representing the annotation.
        """
        deprecate_with_replacement(
            "AnnotationBuilder.text", "pypdf.annotations.Text", "4.0.0"
        )
        from ..annotations import Text

        return Text(rect=rect, text=text, open=open, flags=flags)

    @staticmethod
    def free_text(
        text: str,
        rect: Union[RectangleObject, Tuple[float, float, float, float]],
        font: str = "Helvetica",
        bold: bool = False,
        italic: bool = False,
        font_size: str = "14pt",
        font_color: str = "000000",
        border_color: Optional[str] = "000000",
        background_color: Optional[str] = "ffffff",
    ) -> DictionaryObject:
        """
        Add text in a rectangle to a page.

        Args:
            text: Text to be added
            rect: array of four integers ``[xLL, yLL, xUR, yUR]``
                specifying the clickable rectangular area
            font: Name of the Font, e.g. 'Helvetica'
            bold: Print the text in bold
            italic: Print the text in italic
            font_size: How big the text will be, e.g. '14pt'
            font_color: Hex-string for the color, e.g. cdcdcd
            border_color: Hex-string for the border color, e.g. cdcdcd.
                Use ``None`` for no border.
            background_color: Hex-string for the background of the annotation,
                e.g. cdcdcd. Use ``None`` for transparent background.

        Returns:
            A dictionary object representing the annotation.
        """
        deprecate_with_replacement(
            "AnnotationBuilder.free_text", "pypdf.annotations.FreeText", "4.0.0"
        )
        from ..annotations import FreeText

        return FreeText(
            text=text,
            rect=rect,
            font=font,
            bold=bold,
            italic=italic,
            font_size=font_size,
            font_color=font_color,
            background_color=background_color,
            border_color=border_color,
        )

    @staticmethod
    def popup(
        *,
        rect: Union[RectangleObject, Tuple[float, float, float, float]],
        flags: int = 0,
        parent: Optional[DictionaryObject] = None,
        open: bool = False,
    ) -> DictionaryObject:
        """
        Add a popup to the document.

        Args:
            rect:
                Specifies the clickable rectangular area as `[xLL, yLL, xUR, yUR]`
            flags:
                1 - invisible, 2 - hidden, 3 - print, 4 - no zoom,
                5 - no rotate, 6 - no view, 7 - read only, 8 - locked,
                9 - toggle no view, 10 - locked contents
            open:
                Whether the popup should be shown directly (default is False).
            parent:
                The contents of the popup. Create this via the AnnotationBuilder.

        Returns:
            A dictionary object representing the annotation.
        """
        deprecate_with_replacement(
            "AnnotationBuilder.popup", "pypdf.annotations.Popup", "4.0.0"
        )
        from ..annotations import Popup

        popup = Popup(rect=rect, open=open, parent=parent)
        popup.flags = flags  # type: ignore

        return popup

    @staticmethod
    def line(
        p1: Tuple[float, float],
        p2: Tuple[float, float],
        rect: Union[RectangleObject, Tuple[float, float, float, float]],
        text: str = "",
        title_bar: Optional[str] = None,
    ) -> DictionaryObject:
        """
        Draw a line on the PDF.

        Args:
            p1: First point
            p2: Second point
            rect: array of four integers ``[xLL, yLL, xUR, yUR]``
                specifying the clickable rectangular area
            text: Text to be displayed as the line annotation
            title_bar: Text to be displayed in the title bar of the
                annotation; by convention this is the name of the author

        Returns:
            A dictionary object representing the annotation.
        """
        deprecate_with_replacement(
            "AnnotationBuilder.line", "pypdf.annotations.Line", "4.0.0"
        )
        from ..annotations import Line

        return Line(p1=p1, p2=p2, rect=rect, text=text, title_bar=title_bar)

    @staticmethod
    def polyline(
        vertices: List[Tuple[float, float]],
    ) -> DictionaryObject:
        """
        Draw a polyline on the PDF.

        Args:
            vertices: Array specifying the vertices (x, y) coordinates of the poly-line.

        Returns:
            A dictionary object representing the annotation.
        """
        deprecate_with_replacement(
            "AnnotationBuilder.polyline", "pypdf.annotations.PolyLine", "4.0.0"
        )
        from ..annotations import PolyLine

        return PolyLine(vertices=vertices)

    @staticmethod
    def rectangle(
        rect: Union[RectangleObject, Tuple[float, float, float, float]],
        interiour_color: Optional[str] = None,
    ) -> DictionaryObject:
        """
        Draw a rectangle on the PDF.

        This method uses the /Square annotation type of the PDF format.

        Args:
            rect: array of four integers ``[xLL, yLL, xUR, yUR]``
                specifying the clickable rectangular area
            interiour_color: None or hex-string for the color, e.g. cdcdcd
                If None is used, the interiour is transparent.

        Returns:
            A dictionary object representing the annotation.
        """
        deprecate_with_replacement(
            "AnnotationBuilder.rectangle", "pypdf.annotations.Rectangle", "4.0.0"
        )
        from ..annotations import Rectangle

        return Rectangle(rect=rect, interiour_color=interiour_color)

    @staticmethod
    def highlight(
        *,
        rect: Union[RectangleObject, Tuple[float, float, float, float]],
        quad_points: ArrayObject,
        highlight_color: str = "ff0000",
    ) -> DictionaryObject:
        """
        Add a highlight annotation to the document.

        Args:
            rect: Array of four integers ``[xLL, yLL, xUR, yUR]``
                specifying the highlighted area
            quad_points: An ArrayObject of 8 FloatObjects. Must match a word or
                a group of words, otherwise no highlight will be shown.
            highlight_color: The color used for the highlight.

        Returns:
            A dictionary object representing the annotation.
        """
        deprecate_with_replacement(
            "AnnotationBuilder.highlight", "pypdf.annotations.Highlight", "4.0.0"
        )
        from ..annotations import Highlight

        return Highlight(
            rect=rect, quad_points=quad_points, highlight_color=highlight_color
        )

    @staticmethod
    def ellipse(
        rect: Union[RectangleObject, Tuple[float, float, float, float]],
        interiour_color: Optional[str] = None,
    ) -> DictionaryObject:
        """
        Draw a rectangle on the PDF.

        This method uses the /Circle annotation type of the PDF format.

        Args:
            rect: array of four integers ``[xLL, yLL, xUR, yUR]`` specifying
                the bounding box of the ellipse
            interiour_color: None or hex-string for the color, e.g. cdcdcd
                If None is used, the interiour is transparent.

        Returns:
            A dictionary object representing the annotation.
        """
        deprecate_with_replacement(
            "AnnotationBuilder.ellipse", "pypdf.annotations.Ellipse", "4.0.0"
        )
        from ..annotations import Ellipse

        return Ellipse(rect=rect, interiour_color=interiour_color)

    @staticmethod
    def polygon(vertices: List[Tuple[float, float]]) -> DictionaryObject:
        deprecate_with_replacement(
            "AnnotationBuilder.polygon", "pypdf.annotations.Polygon", "4.0.0"
        )
        from ..annotations import Polygon

        return Polygon(vertices=vertices)

    from ._fit import DEFAULT_FIT

    @staticmethod
    def link(
        rect: Union[RectangleObject, Tuple[float, float, float, float]],
        border: Optional[ArrayObject] = None,
        url: Optional[str] = None,
        target_page_index: Optional[int] = None,
        fit: Fit = DEFAULT_FIT,
    ) -> DictionaryObject:
        """
        Add a link to the document.

        The link can either be an external link or an internal link.

        An external link requires the URL parameter.
        An internal link requires the target_page_index, fit, and fit args.

        Args:
            rect: array of four integers ``[xLL, yLL, xUR, yUR]``
                specifying the clickable rectangular area
            border: if provided, an array describing border-drawing
                properties. See the PDF spec for details. No border will be
                drawn if this argument is omitted.
                - horizontal corner radius,
                - vertical corner radius, and
                - border width
                - Optionally: Dash
            url: Link to a website (if you want to make an external link)
            target_page_index: index of the page to which the link should go
                (if you want to make an internal link)
            fit: Page fit or 'zoom' option.

        Returns:
            A dictionary object representing the annotation.
        """
        deprecate_with_replacement(
            "AnnotationBuilder.link", "pypdf.annotations.Link", "4.0.0"
        )
        from ..annotations import Link

        return Link(
            rect=rect,
            border=border,
            url=url,
            target_page_index=target_page_index,
            fit=fit,
        )


__all__ = [
    # Base types
    "BooleanObject",
    "FloatObject",
    "NumberObject",
    "NameObject",
    "IndirectObject",
    "NullObject",
    "PdfObject",
    "TextStringObject",
    "ByteStringObject",
    # Annotations
    "AnnotationBuilder",
    # Fit
    "Fit",
    "PAGE_FIT",
    # Data structures
    "ArrayObject",
    "DictionaryObject",
    "TreeObject",
    "StreamObject",
    "DecodedStreamObject",
    "EncodedStreamObject",
    "ContentStream",
    "RectangleObject",
    "Field",
    "Destination",
    "ViewerPreferences",
    # --- More specific stuff
    # Outline
    "OutlineItem",
    "OutlineFontFlag",
    # Data structures core functions
    "read_object",
    # Utility functions
    "create_string_object",
    "encode_pdfdocencoding",
    "decode_pdfdocencoding",
    "hex_to_rgb",
    "read_hex_string_from_stream",
    "read_string_from_stream",
]
