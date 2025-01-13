from __future__ import annotations

import optparse
from abc import ABCMeta, abstractmethod
from contextlib import contextmanager
from typing import Iterator

from pip._internal.commands.install import InstallCommand
from pip._internal.index.package_finder import PackageFinder
from pip._internal.models.index import PyPI
from pip._internal.network.session import PipSession
from pip._internal.req import InstallRequirement


class BaseRepository(metaclass=ABCMeta):
    DEFAULT_INDEX_URL = PyPI.simple_url

    def clear_caches(self) -> None:
        """Should clear any caches used by the implementation."""

    @abstractmethod
    def find_best_match(
        self, ireq: InstallRequirement, prereleases: bool | None
    ) -> InstallRequirement:
        """
        Returns a pinned InstallRequirement object that indicates the best match
        for the given InstallRequirement according to the external repository.
        """

    @abstractmethod
    def get_dependencies(self, ireq: InstallRequirement) -> set[InstallRequirement]:
        """
        Given a pinned, URL, or editable InstallRequirement, returns a set of
        dependencies (also InstallRequirements, but not necessarily pinned).
        They indicate the secondary dependencies for the given requirement.
        """

    @abstractmethod
    def get_hashes(self, ireq: InstallRequirement) -> set[str]:
        """
        Given a pinned InstallRequirement, returns a set of hashes that represent
        all of the files for a given requirement. It is not acceptable for an
        editable or unpinned requirement to be passed to this function.
        """

    @abstractmethod
    @contextmanager
    def allow_all_wheels(self) -> Iterator[None]:
        """
        Monkey patches pip.Wheel to allow wheels from all platforms and Python versions.
        """

    @property
    @abstractmethod
    def options(self) -> optparse.Values:
        """Returns parsed pip options"""

    @property
    @abstractmethod
    def session(self) -> PipSession:
        """Returns a session to make requests"""

    @property
    @abstractmethod
    def finder(self) -> PackageFinder:
        """Returns a package finder to interact with simple repository API (PEP 503)"""

    @property
    @abstractmethod
    def command(self) -> InstallCommand:
        """Return an install command."""
