"""Code in here is only used by pypdf.filters._xobj_to_image"""

import sys
from io import BytesIO
from typing import Any, List, Tuple, Union, cast

from ._utils import check_if_whitespace_only, logger_warning
from .constants import ColorSpaces
from .errors import PdfReadError
from .generic import (
    ArrayObject,
    DecodedStreamObject,
    EncodedStreamObject,
    IndirectObject,
    NullObject,
)

if sys.version_info[:2] >= (3, 8):
    from typing import Literal
else:
    # PEP 586 introduced typing.Literal with Python 3.8
    # For older Python versions, the backport typing_extensions is necessary:
    from typing_extensions import Literal

if sys.version_info[:2] >= (3, 10):
    from typing import TypeAlias
else:
    from typing_extensions import TypeAlias


try:
    from PIL import Image
except ImportError:
    raise ImportError(
        "pillow is required to do image extraction. "
        "It can be installed via 'pip install pypdf[image]'"
    )

mode_str_type: TypeAlias = Literal[
    "", "1", "RGB", "2bits", "4bits", "P", "L", "RGBA", "CMYK"
]

MAX_IMAGE_MODE_NESTING_DEPTH: int = 10


def _get_imagemode(
    color_space: Union[str, List[Any], Any],
    color_components: int,
    prev_mode: mode_str_type,
    depth: int = 0,
) -> Tuple[mode_str_type, bool]:
    """
    Returns
        Image mode not taking into account mask(transparency)
        ColorInversion is required (like for some DeviceCMYK)
    """
    if depth > MAX_IMAGE_MODE_NESTING_DEPTH:
        raise PdfReadError(
            "Color spaces nested too deep. If required, consider increasing MAX_IMAGE_MODE_NESTING_DEPTH."
        )
    if isinstance(color_space, NullObject):
        return "", False
    if isinstance(color_space, str):
        pass
    elif not isinstance(color_space, list):
        raise PdfReadError(
            "Cannot interpret colorspace", color_space
        )  # pragma: no cover
    elif color_space[0].startswith("/Cal"):  # /CalRGB and /CalGray
        color_space = "/Device" + color_space[0][4:]
    elif color_space[0] == "/ICCBased":
        icc_profile = color_space[1].get_object()
        color_components = cast(int, icc_profile["/N"])
        color_space = icc_profile.get("/Alternate", "")
    elif color_space[0] == "/Indexed":
        color_space = color_space[1]
        if isinstance(color_space, IndirectObject):
            color_space = color_space.get_object()
        mode2, invert_color = _get_imagemode(
            color_space, color_components, prev_mode, depth + 1
        )
        if mode2 in ("RGB", "CMYK"):
            mode2 = "P"
        return mode2, invert_color
    elif color_space[0] == "/Separation":
        color_space = color_space[2]
        if isinstance(color_space, IndirectObject):
            color_space = color_space.get_object()
        mode2, invert_color = _get_imagemode(
            color_space, color_components, prev_mode, depth + 1
        )
        return mode2, True
    elif color_space[0] == "/DeviceN":
        original_color_space = color_space
        color_components = len(color_space[1])
        color_space = color_space[2]
        if isinstance(color_space, IndirectObject):  # pragma: no cover
            color_space = color_space.get_object()
        if color_space == "/DeviceCMYK" and color_components == 1:
            if original_color_space[1][0] != "/Black":
                logger_warning(
                    f"Color {original_color_space[1][0]} converted to Gray. Please share PDF with pypdf dev team",
                    __name__,
                )
            return "L", True
        mode2, invert_color = _get_imagemode(
            color_space, color_components, prev_mode, depth + 1
        )
        return mode2, invert_color

    mode_map = {
        "1bit": "1",  # pos [0] will be used for 1 bit
        "/DeviceGray": "L",  # must be in pos [1]
        "palette": "P",  # must be in pos [2] for color_components align.
        "/DeviceRGB": "RGB",  # must be in pos [3]
        "/DeviceCMYK": "CMYK",  # must be in pos [4]
        "2bit": "2bits",  # 2 bits images
        "4bit": "4bits",  # 4 bits
    }
    mode: mode_str_type = (
        mode_map.get(color_space)  # type: ignore
        or list(mode_map.values())[color_components]
        or prev_mode
    )
    return mode, mode == "CMYK"


def _handle_flate(
    size: Tuple[int, int],
    data: bytes,
    mode: mode_str_type,
    color_space: str,
    colors: int,
    obj_as_text: str,
) -> Tuple[Image.Image, str, str, bool]:
    """
    Process image encoded in flateEncode
    Returns img, image_format, extension, color inversion
    """

    def bits2byte(data: bytes, size: Tuple[int, int], bits: int) -> bytes:
        mask = (2 << bits) - 1
        nbuff = bytearray(size[0] * size[1])
        by = 0
        bit = 8 - bits
        for y in range(size[1]):
            if (bit != 0) and (bit != 8 - bits):
                by += 1
                bit = 8 - bits
            for x in range(size[0]):
                nbuff[y * size[0] + x] = (data[by] >> bit) & mask
                bit -= bits
                if bit < 0:
                    by += 1
                    bit = 8 - bits
        return bytes(nbuff)

    extension = ".png"  # mime_type = "image/png"
    image_format = "PNG"
    lookup: Any
    base: Any
    hival: Any
    if isinstance(color_space, ArrayObject) and color_space[0] == "/Indexed":
        color_space, base, hival, lookup = (value.get_object() for value in color_space)
    if mode == "2bits":
        mode = "P"
        data = bits2byte(data, size, 2)
    elif mode == "4bits":
        mode = "P"
        data = bits2byte(data, size, 4)
    img = Image.frombytes(mode, size, data)
    if color_space == "/Indexed":
        from .generic import TextStringObject

        if isinstance(lookup, (EncodedStreamObject, DecodedStreamObject)):
            lookup = lookup.get_data()
        if isinstance(lookup, TextStringObject):
            lookup = lookup.original_bytes
        if isinstance(lookup, str):
            lookup = lookup.encode()
        try:
            nb, conv, mode = {  # type: ignore
                "1": (0, "", ""),
                "L": (1, "P", "L"),
                "P": (0, "", ""),
                "RGB": (3, "P", "RGB"),
                "CMYK": (4, "P", "CMYK"),
            }[_get_imagemode(base, 0, "")[0]]
        except KeyError:  # pragma: no cover
            logger_warning(
                f"Base {base} not coded please share the pdf file with pypdf dev team",
                __name__,
            )
            lookup = None
        else:
            if img.mode == "1":
                # Two values ("high" and "low").
                expected_count = 2 * nb
                if len(lookup) != expected_count:
                    if len(lookup) < expected_count:
                        raise PdfReadError(
                            f"Not enough lookup values: Expected {expected_count}, got {len(lookup)}."
                        )
                    if not check_if_whitespace_only(lookup[expected_count:]):
                        raise PdfReadError(
                            f"Too many lookup values: Expected {expected_count}, got {len(lookup)}."
                        )
                    lookup = lookup[:expected_count]
                colors_arr = [lookup[:nb], lookup[nb:]]
                arr = b"".join(
                    [
                        b"".join(
                            [
                                colors_arr[1 if img.getpixel((x, y)) > 127 else 0]
                                for x in range(img.size[0])
                            ]
                        )
                        for y in range(img.size[1])
                    ]
                )
                img = Image.frombytes(mode, img.size, arr)
            else:
                img = img.convert(conv)
                if len(lookup) != (hival + 1) * nb:
                    logger_warning(f"Invalid Lookup Table in {obj_as_text}", __name__)
                    lookup = None
                elif mode == "L":
                    # gray lookup does not work : it is converted to a similar RGB lookup
                    lookup = b"".join([bytes([b, b, b]) for b in lookup])
                    mode = "RGB"
                # TODO : cf https://github.com/py-pdf/pypdf/pull/2039
                # this is a work around until PIL is able to process CMYK images
                elif mode == "CMYK":
                    _rgb = []
                    for _c, _m, _y, _k in (
                        lookup[n : n + 4] for n in range(0, 4 * (len(lookup) // 4), 4)
                    ):
                        _r = int(255 * (1 - _c / 255) * (1 - _k / 255))
                        _g = int(255 * (1 - _m / 255) * (1 - _k / 255))
                        _b = int(255 * (1 - _y / 255) * (1 - _k / 255))
                        _rgb.append(bytes((_r, _g, _b)))
                    lookup = b"".join(_rgb)
                    mode = "RGB"
                if lookup is not None:
                    img.putpalette(lookup, rawmode=mode)
            img = img.convert("L" if base == ColorSpaces.DEVICE_GRAY else "RGB")
    elif not isinstance(color_space, NullObject) and color_space[0] == "/ICCBased":
        # see Table 66 - Additional Entries Specific to an ICC Profile
        # Stream Dictionary
        mode2 = _get_imagemode(color_space, colors, mode)[0]
        if mode != mode2:
            img = Image.frombytes(mode2, size, data)  # reloaded as mode may have change
    if mode == "CMYK":
        extension = ".tif"
        image_format = "TIFF"
    return img, image_format, extension, False


def _handle_jpx(
    size: Tuple[int, int],
    data: bytes,
    mode: mode_str_type,
    color_space: str,
    colors: int,
) -> Tuple[Image.Image, str, str, bool]:
    """
    Process image encoded in flateEncode
    Returns img, image_format, extension, inversion
    """
    extension = ".jp2"  # mime_type = "image/x-jp2"
    img1 = Image.open(BytesIO(data), formats=("JPEG2000",))
    mode, invert_color = _get_imagemode(color_space, colors, mode)
    if mode == "":
        mode = cast(mode_str_type, img1.mode)
        invert_color = mode in ("CMYK",)
    if img1.mode == "RGBA" and mode == "RGB":
        mode = "RGBA"
    # we need to convert to the good mode
    try:
        if img1.mode != mode:
            img = Image.frombytes(mode, img1.size, img1.tobytes())
        else:
            img = img1
    except OSError:
        img = Image.frombytes(mode, img1.size, img1.tobytes())
    # for CMYK conversion :
    # https://stcom/questions/38855022/conversion-from-cmyk-to-rgb-with-pillow-is-different-from-that-of-photoshop
    # not implemented for the moment as I need to get properly the ICC
    if img.mode == "CMYK":
        img = img.convert("RGB")
    image_format = "JPEG2000"
    return img, image_format, extension, invert_color
