import re
from decimal import Decimal
from html import unescape
from math import atan2, cos, radians, sin, sqrt
from typing import Any, Dict, List, Union
from urllib.parse import unquote

import orjson

from .exceptions import DuckDuckGoSearchException

REGEX_STRIP_TAGS = re.compile("<.*?>")


def json_dumps(obj: Any) -> str:
    try:
        return orjson.dumps(obj).decode("utf-8")
    except Exception as ex:
        raise DuckDuckGoSearchException(f"{type(ex).__name__}: {ex}") from ex


def json_loads(obj: Union[str, bytes]) -> Any:
    try:
        return orjson.loads(obj)
    except Exception as ex:
        raise DuckDuckGoSearchException(f"{type(ex).__name__}: {ex}") from ex


def _extract_vqd(html_bytes: bytes, keywords: str) -> str:
    """Extract vqd from html bytes."""
    for c1, c1_len, c2 in (
        (b'vqd="', 5, b'"'),
        (b"vqd=", 4, b"&"),
        (b"vqd='", 5, b"'"),
    ):
        try:
            start = html_bytes.index(c1) + c1_len
            end = html_bytes.index(c2, start)
            return html_bytes[start:end].decode()
        except ValueError:
            pass
    raise DuckDuckGoSearchException(f"_extract_vqd() {keywords=} Could not extract vqd.")


def _text_extract_json(html_bytes: bytes, keywords: str) -> List[Dict[str, str]]:
    """text(backend="api") -> extract json from html."""
    try:
        start = html_bytes.index(b"DDG.pageLayout.load('d',") + 24
        end = html_bytes.index(b");DDG.duckbar.load(", start)
        data = html_bytes[start:end]
        result: List[Dict[str, str]] = json_loads(data)
        return result
    except Exception as ex:
        raise DuckDuckGoSearchException(f"_text_extract_json() {keywords=} {type(ex).__name__}: {ex}") from ex
    raise DuckDuckGoSearchException(f"_text_extract_json() {keywords=} return None")


def _normalize(raw_html: str) -> str:
    """Strip HTML tags from the raw_html string."""
    return unescape(REGEX_STRIP_TAGS.sub("", raw_html)) if raw_html else ""


def _normalize_url(url: str) -> str:
    """Unquote URL and replace spaces with '+'."""
    return unquote(url.replace(" ", "+")) if url else ""


def _calculate_distance(lat1: Decimal, lon1: Decimal, lat2: Decimal, lon2: Decimal) -> float:
    """Calculate distance between two points in km. Haversine formula."""
    R = 6371.0087714  # Earth's radius in km
    rlat1, rlon1, rlat2, rlon2 = map(radians, [float(lat1), float(lon1), float(lat2), float(lon2)])
    dlon, dlat = rlon2 - rlon1, rlat2 - rlat1
    a = sin(dlat / 2) ** 2 + cos(rlat1) * cos(rlat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c
