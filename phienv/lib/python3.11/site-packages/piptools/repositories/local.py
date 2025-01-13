from __future__ import annotations

import optparse
from contextlib import contextmanager
from typing import Iterator, Mapping, cast

from pip._internal.commands.install import InstallCommand
from pip._internal.index.package_finder import PackageFinder
from pip._internal.models.candidate import InstallationCandidate
from pip._internal.network.session import PipSession
from pip._internal.req import InstallRequirement
from pip._internal.utils.hashes import FAVORITE_HASH

from piptools.utils import as_tuple, key_from_ireq, make_install_requirement

from .base import BaseRepository
from .pypi import PyPIRepository


def ireq_satisfied_by_existing_pin(
    ireq: InstallRequirement, existing_pin: InstallationCandidate
) -> bool:
    """
    Return True if the given InstallationRequirement is satisfied by the
    previously encountered version pin.
    """
    version = next(iter(existing_pin.req.specifier)).version
    result = ireq.req.specifier.contains(
        version, prereleases=existing_pin.req.specifier.prereleases
    )
    return cast(bool, result)


class LocalRequirementsRepository(BaseRepository):
    """
    The LocalRequirementsRepository proxied the _real_ repository by first
    checking if a requirement can be satisfied by existing pins (i.e. the
    result of a previous compile step).

    In effect, if a requirement can be satisfied with a version pinned in the
    requirements file, we prefer that version over the best match found in
    PyPI.  This keeps updates to the requirements.txt down to a minimum.
    """

    def __init__(
        self,
        existing_pins: Mapping[str, InstallationCandidate],
        proxied_repository: PyPIRepository,
        reuse_hashes: bool = True,
    ):
        self._reuse_hashes = reuse_hashes
        self.repository = proxied_repository
        self.existing_pins = existing_pins

    @property
    def options(self) -> optparse.Values:
        return self.repository.options

    @property
    def finder(self) -> PackageFinder:
        return self.repository.finder

    @property
    def session(self) -> PipSession:
        return self.repository.session

    @property
    def command(self) -> InstallCommand:
        """Return an install command instance."""
        return self.repository.command

    def clear_caches(self) -> None:
        self.repository.clear_caches()

    def find_best_match(
        self, ireq: InstallRequirement, prereleases: bool | None = None
    ) -> InstallationCandidate:
        key = key_from_ireq(ireq)
        existing_pin = self.existing_pins.get(key)
        if existing_pin and ireq_satisfied_by_existing_pin(ireq, existing_pin):
            project, version, _ = as_tuple(existing_pin)
            return make_install_requirement(project, version, ireq)
        else:
            return self.repository.find_best_match(ireq, prereleases)

    def get_dependencies(self, ireq: InstallRequirement) -> set[InstallRequirement]:
        return self.repository.get_dependencies(ireq)

    def get_hashes(self, ireq: InstallRequirement) -> set[str]:
        existing_pin = self._reuse_hashes and self.existing_pins.get(
            key_from_ireq(ireq)
        )
        if existing_pin and ireq_satisfied_by_existing_pin(ireq, existing_pin):
            hashes = existing_pin.hash_options
            hexdigests = hashes.get(FAVORITE_HASH)
            if hexdigests:
                return {
                    ":".join([FAVORITE_HASH, hexdigest]) for hexdigest in hexdigests
                }
        return self.repository.get_hashes(ireq)

    @contextmanager
    def allow_all_wheels(self) -> Iterator[None]:
        with self.repository.allow_all_wheels():
            yield
