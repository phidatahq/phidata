from __future__ import annotations

import json
import os
import platform
import sys
from typing import Dict, Iterable, List, Tuple, cast

from pip._internal.req import InstallRequirement
from pip._vendor.packaging.requirements import Requirement

from .exceptions import PipToolsError
from .utils import as_tuple, key_from_req, lookup_table_from_tuples

CacheKey = Tuple[str, str]
CacheLookup = Dict[str, List[str]]
CacheDict = Dict[str, CacheLookup]

_PEP425_PY_TAGS = {"cpython": "cp", "pypy": "pp", "ironpython": "ip", "jython": "jy"}


def _implementation_name() -> str:
    """
    Similar to PEP 425, however the minor version is separated from the major to
    differentiate "3.10" and "31.0".
    """
    implementation_name = platform.python_implementation().lower()
    implementation = _PEP425_PY_TAGS.get(implementation_name, "??")
    return "{}{}.{}".format(implementation, *sys.version_info)


class CorruptCacheError(PipToolsError):
    def __init__(self, path: str):
        self.path = path

    def __str__(self) -> str:
        lines = [
            "The dependency cache seems to have been corrupted.",
            "Inspect, or delete, the following file:",
            f"  {self.path}",
        ]
        return os.linesep.join(lines)


def read_cache_file(cache_file_path: str) -> CacheDict:
    with open(cache_file_path, encoding="utf-8") as cache_file:
        try:
            doc = json.load(cache_file)
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise CorruptCacheError(cache_file_path)

        # Check version and load the contents
        if doc["__format__"] != 1:
            raise ValueError("Unknown cache file format")
        return cast(CacheDict, doc["dependencies"])


class DependencyCache:
    """
    Creates a new persistent dependency cache for the current Python version.
    The cache file is written to the appropriate user cache dir for the
    current platform, i.e.

        ~/.cache/pip-tools/depcache-pyX.Y.json

    Where py indicates the Python implementation.
    Where X.Y indicates the Python version.
    """

    def __init__(self, cache_dir: str):
        os.makedirs(cache_dir, exist_ok=True)
        cache_filename = f"depcache-{_implementation_name()}.json"

        self._cache_file = os.path.join(cache_dir, cache_filename)
        self._cache: CacheDict | None = None

    @property
    def cache(self) -> CacheDict:
        """
        The dictionary that is the actual in-memory cache.  This property
        lazily loads the cache from disk.
        """
        if self._cache is None:
            try:
                self._cache = read_cache_file(self._cache_file)
            except FileNotFoundError:
                self._cache = {}
        return self._cache

    def as_cache_key(self, ireq: InstallRequirement) -> CacheKey:
        """
        Given a requirement, return its cache key. This behavior is a little weird
        in order to allow backwards compatibility with cache files. For a requirement
        without extras, this will return, for example:

        ("ipython", "2.1.0")

        For a requirement with extras, the extras will be comma-separated and appended
        to the version, inside brackets, like so:

        ("ipython", "2.1.0[nbconvert,notebook]")
        """
        name, version, extras = as_tuple(ireq)
        if not extras:
            extras_string = ""
        else:
            extras_string = f"[{','.join(extras)}]"
        return name, f"{version}{extras_string}"

    def write_cache(self) -> None:
        """Writes the cache to disk as JSON."""
        doc = {"__format__": 1, "dependencies": self._cache}
        with open(self._cache_file, "w", encoding="utf-8") as f:
            json.dump(doc, f, sort_keys=True)

    def clear(self) -> None:
        self._cache = {}
        self.write_cache()

    def __contains__(self, ireq: InstallRequirement) -> bool:
        pkgname, pkgversion_and_extras = self.as_cache_key(ireq)
        return pkgversion_and_extras in self.cache.get(pkgname, {})

    def __getitem__(self, ireq: InstallRequirement) -> list[str]:
        pkgname, pkgversion_and_extras = self.as_cache_key(ireq)
        return self.cache[pkgname][pkgversion_and_extras]

    def __setitem__(self, ireq: InstallRequirement, values: list[str]) -> None:
        pkgname, pkgversion_and_extras = self.as_cache_key(ireq)
        self.cache.setdefault(pkgname, {})
        self.cache[pkgname][pkgversion_and_extras] = values
        self.write_cache()

    def reverse_dependencies(
        self, ireqs: Iterable[InstallRequirement]
    ) -> dict[str, set[str]]:
        """
        Returns a lookup table of reverse dependencies for all the given ireqs.

        Since this is all static, it only works if the dependency cache
        contains the complete data, otherwise you end up with a partial view.
        This is typically no problem if you use this function after the entire
        dependency tree is resolved.
        """
        ireqs_as_cache_values = [self.as_cache_key(ireq) for ireq in ireqs]
        return self._reverse_dependencies(ireqs_as_cache_values)

    def _reverse_dependencies(
        self, cache_keys: Iterable[tuple[str, str]]
    ) -> dict[str, set[str]]:
        """
        Returns a lookup table of reverse dependencies for all the given cache keys.

        Example input:

            [('pep8', '1.5.7'),
             ('flake8', '2.4.0'),
             ('mccabe', '0.3'),
             ('pyflakes', '0.8.1')]

        Example output:

            {'pep8': ['flake8'],
             'flake8': [],
             'mccabe': ['flake8'],
             'pyflakes': ['flake8']}

        """
        # First, collect all the dependencies into a sequence of (parent, child)
        # tuples, like [('flake8', 'pep8'), ('flake8', 'mccabe'), ...]
        return lookup_table_from_tuples(
            (key_from_req(Requirement(dep_name)), name)
            for name, version_and_extras in cache_keys
            for dep_name in self.cache[name][version_and_extras]
        )
