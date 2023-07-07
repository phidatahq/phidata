# Copyright 2014 Donald Stufft
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import functools
from typing import Any, Dict, Iterator, List, Optional

import bleach
import bleach.callbacks
import bleach.linkifier
import bleach.sanitizer


ALLOWED_TAGS = [
    # Bleach Defaults
    "a", "abbr", "acronym", "b", "blockquote", "code", "em", "i", "li", "ol",
    "strong", "ul",

    # Custom Additions
    "br", "caption", "cite", "col", "colgroup", "dd", "del", "details", "div",
    "dl", "dt", "h1", "h2", "h3", "h4", "h5", "h6", "hr", "img", "p", "pre",
    "span", "sub", "summary", "sup", "table", "tbody", "td", "th", "thead",
    "tr", "tt", "kbd", "var", "input", "section", "aside", "nav", "s", "figure",
]

ALLOWED_ATTRIBUTES = {
    # Bleach Defaults
    "a": ["href", "title"],
    "abbr": ["title"],
    "acronym": ["title"],

    # Custom Additions
    "*": ["id"],
    "hr": ["class"],
    "img": ["src", "width", "height", "alt", "align", "class"],
    "span": ["class"],
    "th": ["align", "class"],
    "td": ["align", "colspan", "rowspan"],
    "div": ["align", "class"],
    "h1": ["align"],
    "h2": ["align"],
    "h3": ["align"],
    "h4": ["align"],
    "h5": ["align"],
    "h6": ["align"],
    "code": ["class"],
    "p": ["align", "class"],
    "pre": ["lang"],
    "ol": ["start"],
    "input": ["type", "checked", "disabled"],
    "aside": ["class"],
    "dd": ["class"],
    "dl": ["class"],
    "dt": ["class"],
    "ul": ["class"],
    "nav": ["class"],
    "figure": ["class"],
}


class DisabledCheckboxInputsFilter:
    # The typeshed for bleach (html5lib) filters is incomplete, use `typing.Any`
    # See https://github.com/python/typeshed/blob/505ea726415016e53638c8b584b8fdc9c722cac1/stubs/bleach/bleach/html5lib_shim.pyi#L7-L8 # noqa E501
    def __init__(self, source: Any) -> None:
        self.source = source

    def __iter__(self) -> Iterator[Dict[str, Optional[str]]]:
        for token in self.source:
            if token.get("name") == "input":
                # only allow disabled checkbox inputs
                is_checkbox, is_disabled, unsafe_attrs = False, False, False
                for (_, attrname), value in token.get("data", {}).items():
                    if attrname == "type" and value == "checkbox":
                        is_checkbox = True
                    elif attrname == "disabled":
                        is_disabled = True
                    elif attrname != "checked":
                        unsafe_attrs = True
                        break
                if is_checkbox and is_disabled and not unsafe_attrs:
                    yield token
            else:
                yield token

    def __getattr__(self, name: str) -> Any:
        return getattr(self.source, name)


def clean(
    html: str,
    tags: Optional[List[str]] = None,
    attributes: Optional[Dict[str, List[str]]] = None
) -> Optional[str]:
    if tags is None:
        tags = ALLOWED_TAGS
    if attributes is None:
        attributes = ALLOWED_ATTRIBUTES

    # Clean the output using Bleach
    cleaner = bleach.sanitizer.Cleaner(
        tags=tags,
        attributes=attributes,
        filters=[
            # Bleach Linkify makes it easy to modify links, however, we will
            # not be using it to create additional links.
            functools.partial(
                bleach.linkifier.LinkifyFilter,
                callbacks=[
                    lambda attrs, new: attrs if not new else None,
                    bleach.callbacks.nofollow,
                ],
                skip_tags=["pre"],
                parse_email=False,
            ),
            DisabledCheckboxInputsFilter,
        ],
    )
    try:
        cleaned = cleaner.clean(html)
        return cleaned
    except ValueError:
        return None
