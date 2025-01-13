from __future__ import annotations

import contextlib
import hashlib
import itertools
import optparse
import os
from contextlib import contextmanager
from shutil import rmtree
from typing import Any, BinaryIO, ContextManager, Iterator, NamedTuple

from click import progressbar
from pip._internal.cache import WheelCache
from pip._internal.commands import create_command
from pip._internal.commands.install import InstallCommand
from pip._internal.index.package_finder import PackageFinder
from pip._internal.models.candidate import InstallationCandidate
from pip._internal.models.index import PackageIndex
from pip._internal.models.link import Link
from pip._internal.models.wheel import Wheel
from pip._internal.network.session import PipSession
from pip._internal.operations.build.build_tracker import get_build_tracker
from pip._internal.req import InstallRequirement, RequirementSet
from pip._internal.utils.hashes import FAVORITE_HASH
from pip._internal.utils.logging import indent_log, setup_logging
from pip._internal.utils.misc import normalize_path
from pip._internal.utils.temp_dir import TempDirectory, global_tempdir_manager
from pip._internal.utils.urls import path_to_url, url_to_path
from pip._vendor.packaging.tags import Tag
from pip._vendor.packaging.version import _BaseVersion
from pip._vendor.requests import RequestException, Session

from .._compat import create_wheel_cache
from ..exceptions import NoCandidateFound
from ..logging import log
from ..utils import (
    as_tuple,
    is_pinned_requirement,
    is_url_requirement,
    lookup_table,
    make_install_requirement,
)
from .base import BaseRepository

FILE_CHUNK_SIZE = 4096


class FileStream(NamedTuple):
    stream: BinaryIO
    size: float | None


class PyPIRepository(BaseRepository):
    HASHABLE_PACKAGE_TYPES = {"bdist_wheel", "sdist"}

    """
    The PyPIRepository will use the provided Finder instance to lookup
    packages.  Typically, it looks up packages on PyPI (the default implicit
    config), but any other PyPI mirror can be used if index_urls is
    changed/configured on the Finder.
    """

    def __init__(self, pip_args: list[str], cache_dir: str):
        # Use pip's parser for pip.conf management and defaults.
        # General options (find_links, index_url, extra_index_url, trusted_host,
        # and pre) are deferred to pip.
        self._command: InstallCommand = create_command("install")

        options, _ = self.command.parse_args(pip_args)
        if options.cache_dir:
            options.cache_dir = normalize_path(options.cache_dir)
        options.require_hashes = False
        options.ignore_dependencies = False

        self._options: optparse.Values = options
        self._session = self.command._build_session(options)
        self._finder = self.command._build_package_finder(
            options=options, session=self.session
        )

        # Caches
        # stores project_name => InstallationCandidate mappings for all
        # versions reported by PyPI, so we only have to ask once for each
        # project
        self._available_candidates_cache: dict[str, list[InstallationCandidate]] = {}

        # stores InstallRequirement => list(InstallRequirement) mappings
        # of all secondary dependencies for the given requirement, so we
        # only have to go to disk once for each requirement
        self._dependencies_cache: dict[InstallRequirement, set[InstallRequirement]] = {}

        # Setup file paths
        self._cache_dir = normalize_path(str(cache_dir))
        self._download_dir = os.path.join(self._cache_dir, "pkgs")

        # Default pip's logger is noisy, so decrease it's verbosity
        setup_logging(
            verbosity=log.verbosity - 1,
            no_color=self.options.no_color,
            user_log_file=self.options.log,
        )

    def clear_caches(self) -> None:
        rmtree(self._download_dir, ignore_errors=True)

    @property
    def options(self) -> optparse.Values:
        return self._options

    @property
    def session(self) -> PipSession:
        return self._session

    @property
    def finder(self) -> PackageFinder:
        return self._finder

    @property
    def command(self) -> InstallCommand:
        """Return an install command instance."""
        return self._command

    def find_all_candidates(self, req_name: str) -> list[InstallationCandidate]:
        if req_name not in self._available_candidates_cache:
            candidates = self.finder.find_all_candidates(req_name)
            self._available_candidates_cache[req_name] = candidates
        return self._available_candidates_cache[req_name]

    def find_best_match(
        self, ireq: InstallRequirement, prereleases: bool | None = None
    ) -> InstallRequirement:
        """
        Returns a pinned InstallRequirement object that indicates the best match
        for the given InstallRequirement according to the external repository.
        """
        if ireq.editable or is_url_requirement(ireq):
            return ireq  # return itself as the best match

        all_candidates = self.find_all_candidates(ireq.name)
        candidates_by_version = lookup_table(all_candidates, key=candidate_version)
        matching_versions = ireq.specifier.filter(
            (candidate.version for candidate in all_candidates), prereleases=prereleases
        )

        matching_candidates = list(
            itertools.chain.from_iterable(
                candidates_by_version[ver] for ver in matching_versions
            )
        )
        if not matching_candidates:
            raise NoCandidateFound(ireq, all_candidates, self.finder)

        evaluator = self.finder.make_candidate_evaluator(ireq.name)
        best_candidate_result = evaluator.compute_best_candidate(matching_candidates)
        best_candidate = best_candidate_result.best_candidate

        # Turn the candidate into a pinned InstallRequirement
        return make_install_requirement(
            best_candidate.name,
            best_candidate.version,
            ireq,
        )

    def resolve_reqs(
        self,
        download_dir: str | None,
        ireq: InstallRequirement,
        wheel_cache: WheelCache,
    ) -> set[InstallationCandidate]:
        with get_build_tracker() as build_tracker, TempDirectory(
            kind="resolver"
        ) as temp_dir, indent_log():
            preparer_kwargs = {
                "temp_build_dir": temp_dir,
                "options": self.options,
                "session": self.session,
                "finder": self.finder,
                "use_user_site": False,
                "download_dir": download_dir,
                "build_tracker": build_tracker,
            }
            preparer = self.command.make_requirement_preparer(**preparer_kwargs)

            reqset = RequirementSet()
            ireq.user_supplied = True
            if getattr(ireq, "name", None):
                reqset.add_named_requirement(ireq)
            else:
                reqset.add_unnamed_requirement(ireq)

            resolver = self.command.make_resolver(
                preparer=preparer,
                finder=self.finder,
                options=self.options,
                wheel_cache=wheel_cache,
                use_user_site=False,
                ignore_installed=True,
                ignore_requires_python=False,
                force_reinstall=False,
                upgrade_strategy="to-satisfy-only",
            )
            results = resolver._resolve_one(reqset, ireq)
            if not ireq.prepared:
                # If still not prepared, e.g. a constraint, do enough to assign
                # the ireq a name:
                resolver._get_dist_for(ireq)

        return set(results)

    def get_dependencies(self, ireq: InstallRequirement) -> set[InstallRequirement]:
        """
        Given a pinned, URL, or editable InstallRequirement, returns a set of
        dependencies (also InstallRequirements, but not necessarily pinned).
        They indicate the secondary dependencies for the given requirement.
        """
        if not (
            ireq.editable or is_url_requirement(ireq) or is_pinned_requirement(ireq)
        ):
            raise TypeError(
                f"Expected url, pinned or editable InstallRequirement, got {ireq}"
            )

        if ireq not in self._dependencies_cache:
            if ireq.editable and (ireq.source_dir and os.path.exists(ireq.source_dir)):
                # No download_dir for locally available editable requirements.
                # If a download_dir is passed, pip will unnecessarily archive
                # the entire source directory
                download_dir = None
            elif ireq.link and ireq.link.is_vcs:
                # No download_dir for VCS sources.  This also works around pip
                # using git-checkout-index, which gets rid of the .git dir.
                download_dir = None
            else:
                download_dir = self._get_download_path(ireq)
                os.makedirs(download_dir, exist_ok=True)

            with global_tempdir_manager():
                wheel_cache = create_wheel_cache(
                    cache_dir=self._cache_dir,
                    format_control=self.options.format_control,
                )
                self._dependencies_cache[ireq] = self.resolve_reqs(
                    download_dir, ireq, wheel_cache
                )

        return self._dependencies_cache[ireq]

    def _get_project(self, ireq: InstallRequirement) -> Any:
        """
        Return a dict of a project info from PyPI JSON API for a given
        InstallRequirement. Return None on HTTP/JSON error or if a package
        is not found on PyPI server.

        API reference: https://warehouse.readthedocs.io/api-reference/json/
        """
        package_indexes = (
            PackageIndex(url=index_url, file_storage_domain="")
            for index_url in self.finder.search_scope.index_urls
        )
        for package_index in package_indexes:
            url = f"{package_index.pypi_url}/{ireq.name}/json"
            try:
                response = self.session.get(url)
            except RequestException as e:
                log.debug(f"Fetch package info from PyPI failed: {url}: {e}")
                continue

            # Skip this PyPI server, because there is no package
            # or JSON API might be not supported
            if response.status_code == 404:
                continue

            try:
                data = response.json()
            except ValueError as e:
                log.debug(f"Cannot parse JSON response from PyPI: {url}: {e}")
                continue
            return data
        return None

    def _get_download_path(self, ireq: InstallRequirement) -> str:
        """
        Determine the download dir location in a way which avoids name
        collisions.
        """
        if ireq.link:
            salt = hashlib.sha224(ireq.link.url_without_fragment.encode()).hexdigest()
            # Nest directories to avoid running out of top level dirs on some FS
            # (see pypi _get_cache_path_parts, which inspired this)
            return os.path.join(
                self._download_dir, salt[:2], salt[2:4], salt[4:6], salt[6:]
            )
        else:
            return self._download_dir

    def get_hashes(self, ireq: InstallRequirement) -> set[str]:
        """
        Given an InstallRequirement, return a set of hashes that represent all
        of the files for a given requirement. Unhashable requirements return an
        empty set. Unpinned requirements raise a TypeError.
        """

        if ireq.link:
            link = ireq.link

            if link.is_vcs or (link.is_file and link.is_existing_dir()):
                # Return empty set for unhashable requirements.
                # Unhashable logic modeled on pip's
                # RequirementPreparer.prepare_linked_requirement
                return set()

            if is_url_requirement(ireq):
                # Directly hash URL requirements.
                # URL requirements may have been previously downloaded and cached
                # locally by self.resolve_reqs()
                cached_path = os.path.join(self._get_download_path(ireq), link.filename)
                if os.path.exists(cached_path):
                    cached_link = Link(path_to_url(cached_path))
                else:
                    cached_link = link
                return {self._get_file_hash(cached_link)}

        if not is_pinned_requirement(ireq):
            raise TypeError(f"Expected pinned requirement, got {ireq}")

        log.debug(ireq.name)

        with log.indentation():
            return self._get_req_hashes(ireq)

    def _get_req_hashes(self, ireq: InstallRequirement) -> set[str]:
        """
        Collects the hashes for all candidates satisfying the given InstallRequirement. Computes
        the hashes for the candidates that don't have one reported by their index.
        """
        matching_candidates = self._get_matching_candidates(ireq)
        pypi_hashes_by_link = self._get_hashes_from_pypi(ireq)
        pypi_hashes = {
            pypi_hashes_by_link[candidate.link.url]
            for candidate in matching_candidates
            if candidate.link.url in pypi_hashes_by_link
        }
        local_hashes = {
            self._get_file_hash(candidate.link)
            for candidate in matching_candidates
            if candidate.link.url not in pypi_hashes_by_link
        }
        return pypi_hashes | local_hashes

    def _get_hashes_from_pypi(self, ireq: InstallRequirement) -> dict[str, str]:
        """
        Builds a mapping from the release URLs to their hashes as reported by the PyPI JSON API
        for a given InstallRequirement.
        """
        project = self._get_project(ireq)
        if project is None:
            return {}

        _, version, _ = as_tuple(ireq)

        try:
            release_files = project["releases"][version]
        except KeyError:
            log.debug("Missing release files on PyPI")
            return {}

        try:
            hashes = {
                file_["url"]: f"{FAVORITE_HASH}:{file_['digests'][FAVORITE_HASH]}"
                for file_ in release_files
                if file_["packagetype"] in self.HASHABLE_PACKAGE_TYPES
            }
        except KeyError:
            log.debug("Missing digests of release files on PyPI")
            return {}

        return hashes

    def _get_matching_candidates(
        self, ireq: InstallRequirement
    ) -> set[InstallationCandidate]:
        """
        Returns all candidates that satisfy the given InstallRequirement.
        """
        # We need to get all of the candidates that match our current version
        # pin, these will represent all of the files that could possibly
        # satisfy this constraint.
        all_candidates = self.find_all_candidates(ireq.name)
        candidates_by_version = lookup_table(all_candidates, key=candidate_version)
        matching_versions = list(
            ireq.specifier.filter(candidate.version for candidate in all_candidates)
        )
        return candidates_by_version[matching_versions[0]]

    def _get_file_hash(self, link: Link) -> str:
        log.debug(f"Hashing {link.show_url}")
        h = hashlib.new(FAVORITE_HASH)
        with open_local_or_remote_file(link, self.session) as f:
            # Chunks to iterate
            chunks = iter(lambda: f.stream.read(FILE_CHUNK_SIZE), b"")

            # Choose a context manager depending on verbosity
            context_manager: ContextManager[Iterator[bytes]]
            if log.verbosity >= 1:
                iter_length = int(f.size / FILE_CHUNK_SIZE) if f.size else None
                bar_template = f"{' ' * log.current_indent}  |%(bar)s| %(info)s"
                context_manager = progressbar(
                    chunks,
                    length=iter_length,
                    # Make it look like default pip progress bar
                    fill_char="█",
                    empty_char=" ",
                    bar_template=bar_template,
                    width=32,
                )
            else:
                context_manager = contextlib.nullcontext(chunks)

            # Iterate over the chosen context manager
            with context_manager as bar:
                for chunk in bar:
                    h.update(chunk)
        return ":".join([FAVORITE_HASH, h.hexdigest()])

    @contextmanager
    def allow_all_wheels(self) -> Iterator[None]:
        """
        Monkey patches pip.Wheel to allow wheels from all platforms and Python versions.

        This also saves the candidate cache and set a new one, or else the results from
        the previous non-patched calls will interfere.
        """

        def _wheel_supported(self: Wheel, tags: list[Tag]) -> bool:
            # Ignore current platform. Support everything.
            return True

        def _wheel_support_index_min(self: Wheel, tags: list[Tag]) -> int:
            # All wheels are equal priority for sorting.
            return 0

        original_wheel_supported = Wheel.supported
        original_support_index_min = Wheel.support_index_min
        original_cache = self._available_candidates_cache

        Wheel.supported = _wheel_supported
        Wheel.support_index_min = _wheel_support_index_min
        self._available_candidates_cache = {}

        # If we don't clear this cache then it can contain results from an
        # earlier call when allow_all_wheels wasn't active. See GH-1532
        self.finder.find_all_candidates.cache_clear()

        try:
            yield
        finally:
            Wheel.supported = original_wheel_supported
            Wheel.support_index_min = original_support_index_min
            self._available_candidates_cache = original_cache


@contextmanager
def open_local_or_remote_file(link: Link, session: Session) -> Iterator[FileStream]:
    """
    Open local or remote file for reading.

    :type link: pip.index.Link
    :type session: requests.Session
    :raises ValueError: If link points to a local directory.
    :return: a context manager to a FileStream with the opened file-like object
    """
    url = link.url_without_fragment

    if link.is_file:
        # Local URL
        local_path = url_to_path(url)
        if os.path.isdir(local_path):
            raise ValueError(f"Cannot open directory for read: {url}")
        else:
            st = os.stat(local_path)
            with open(local_path, "rb") as local_file:
                yield FileStream(stream=local_file, size=st.st_size)
    else:
        # Remote URL
        headers = {"Accept-Encoding": "identity"}
        response = session.get(url, headers=headers, stream=True)

        # Content length must be int or None
        content_length: int | None
        try:
            content_length = int(response.headers["content-length"])
        except (ValueError, KeyError, TypeError):
            content_length = None

        try:
            yield FileStream(stream=response.raw, size=content_length)
        finally:
            response.close()


def candidate_version(candidate: InstallationCandidate) -> _BaseVersion:
    return candidate.version
