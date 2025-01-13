"""Duckduckgo_search.

Search for words, documents, images, videos, news, maps and text translation
using the DuckDuckGo.com search engine.
"""

import logging

from .duckduckgo_search import DDGS
from .version import __version__

__all__ = ["DDGS", "__version__", "cli"]


# A do-nothing logging handler
# https://docs.python.org/3.3/howto/logging.html#configuring-logging-for-a-library
logging.getLogger("duckduckgo_search").addHandler(logging.NullHandler())
