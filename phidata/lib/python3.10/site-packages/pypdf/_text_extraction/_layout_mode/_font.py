"""Font constants and classes for "layout" mode text operations"""

from dataclasses import dataclass, field
from typing import Any, Dict, Sequence, Union

from ...generic import IndirectObject
from ._font_widths import STANDARD_WIDTHS


@dataclass
class Font:
    """
    A font object formatted for use during "layout" mode text extraction

    Attributes:
        subtype (str): font subtype
        space_width (int | float): width of a space character
        encoding (str | Dict[int, str]): font encoding
        char_map (dict): character map
        font_dictionary (dict): font dictionary
    """

    subtype: str
    space_width: Union[int, float]
    encoding: Union[str, Dict[int, str]]
    char_map: Dict[Any, Any]
    font_dictionary: Dict[Any, Any]
    width_map: Dict[str, int] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        # TrueType fonts have a /Widths array mapping character codes to widths
        if isinstance(self.encoding, dict) and "/Widths" in self.font_dictionary:
            first_char = self.font_dictionary.get("/FirstChar", 0)
            self.width_map = {
                self.encoding.get(idx + first_char, chr(idx + first_char)): width
                for idx, width in enumerate(self.font_dictionary["/Widths"])
            }

        # CID fonts have a /W array mapping character codes to widths stashed in /DescendantFonts
        if "/DescendantFonts" in self.font_dictionary:
            d_font: Dict[Any, Any]
            for d_font_idx, d_font in enumerate(
                self.font_dictionary["/DescendantFonts"]
            ):
                while isinstance(d_font, IndirectObject):
                    d_font = d_font.get_object()  # type: ignore[assignment]
                self.font_dictionary["/DescendantFonts"][d_font_idx] = d_font
                ord_map = {
                    ord(_target): _surrogate
                    for _target, _surrogate in self.char_map.items()
                    if isinstance(_target, str)
                }
                # /W width definitions have two valid formats which can be mixed and matched:
                #   (1) A character start index followed by a list of widths, e.g.
                #       `45 [500 600 700]` applies widths 500, 600, 700 to characters 45-47.
                #   (2) A character start index, a character stop index, and a width, e.g.
                #       `45 65 500` applies width 500 to characters 45-65.
                skip_count = 0
                _w = d_font.get("/W", [])
                for idx, w_entry in enumerate(_w):
                    if skip_count:
                        skip_count -= 1
                        continue
                    if not isinstance(w_entry, (int, float)):  # pragma: no cover
                        # We should never get here due to skip_count above. Add a
                        # warning and or use reader's "strict" to force an ex???
                        continue
                    # check for format (1): `int [int int int int ...]`
                    if isinstance(_w[idx + 1], Sequence):
                        start_idx, width_list = _w[idx : idx + 2]
                        self.width_map.update(
                            {
                                ord_map[_cidx]: _width
                                for _cidx, _width in zip(
                                    range(start_idx, start_idx + len(width_list), 1),
                                    width_list,
                                )
                                if _cidx in ord_map
                            }
                        )
                        skip_count = 1
                    # check for format (2): `int int int`
                    if not isinstance(_w[idx + 1], Sequence) and not isinstance(
                        _w[idx + 2], Sequence
                    ):
                        start_idx, stop_idx, const_width = _w[idx : idx + 3]
                        self.width_map.update(
                            {
                                ord_map[_cidx]: const_width
                                for _cidx in range(start_idx, stop_idx + 1, 1)
                                if _cidx in ord_map
                            }
                        )
                        skip_count = 2
        if not self.width_map and "/BaseFont" in self.font_dictionary:
            for key in STANDARD_WIDTHS:
                if self.font_dictionary["/BaseFont"].startswith(f"/{key}"):
                    self.width_map = STANDARD_WIDTHS[key]
                    break

    def word_width(self, word: str) -> float:
        """Sum of character widths specified in PDF font for the supplied word"""
        return sum(
            [self.width_map.get(char, self.space_width * 2) for char in word], 0.0
        )

    @staticmethod
    def to_dict(font_instance: "Font") -> Dict[str, Any]:
        """Dataclass to dict for json.dumps serialization."""
        return {
            k: getattr(font_instance, k) for k in font_instance.__dataclass_fields__
        }
