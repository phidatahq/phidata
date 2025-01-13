from __future__ import annotations

import collections
import copy
from abc import ABCMeta, abstractmethod
from functools import partial
from itertools import chain, count, groupby
from typing import Any, Container, DefaultDict, Iterable, Iterator

import click
from pip._internal.exceptions import DistributionNotFound
from pip._internal.operations.build.build_tracker import (
    get_build_tracker,
    update_env_context_manager,
)
from pip._internal.req import InstallRequirement
from pip._internal.req.constructors import install_req_from_line
from pip._internal.resolution.resolvelib.base import Candidate
from pip._internal.resolution.resolvelib.candidates import ExtrasCandidate
from pip._internal.resolution.resolvelib.resolver import Resolver
from pip._internal.utils.logging import indent_log
from pip._internal.utils.temp_dir import TempDirectory, global_tempdir_manager
from pip._vendor.packaging.specifiers import SpecifierSet
from pip._vendor.packaging.utils import canonicalize_name
from pip._vendor.resolvelib.resolvers import ResolutionImpossible, Result

from piptools.cache import DependencyCache
from piptools.repositories.base import BaseRepository

from ._compat import create_wheel_cache
from .exceptions import PipToolsError
from .logging import log
from .utils import (
    UNSAFE_PACKAGES,
    as_tuple,
    copy_install_requirement,
    format_requirement,
    format_specifier,
    is_pinned_requirement,
    is_url_requirement,
    key_from_ireq,
    key_from_req,
    omit_list_value,
    strip_extras,
)

green = partial(click.style, fg="green")
magenta = partial(click.style, fg="magenta")


class RequirementSummary:
    """
    Summary of a requirement's properties for comparison purposes.
    """

    def __init__(self, ireq: InstallRequirement) -> None:
        self.req = ireq.req
        self.key = key_from_ireq(ireq)
        self.extras = frozenset(ireq.extras)
        self.specifier = ireq.specifier

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return NotImplemented

        return (
            self.key == other.key
            and self.specifier == other.specifier
            and self.extras == other.extras
        )

    def __hash__(self) -> int:
        return hash((self.key, self.specifier, self.extras))

    def __str__(self) -> str:
        return repr((self.key, str(self.specifier), sorted(self.extras)))


def combine_install_requirements(
    ireqs: Iterable[InstallRequirement],
) -> InstallRequirement:
    """
    Return a single install requirement that reflects a combination of
    all the inputs.
    """
    # We will store the source ireqs in a _source_ireqs attribute;
    # if any of the inputs have this, then use those sources directly.
    source_ireqs: list[InstallRequirement] = []
    for ireq in ireqs:
        source_ireqs.extend(getattr(ireq, "_source_ireqs", [ireq]))

    # Optimization. Don't bother with combination logic.
    if len(source_ireqs) == 1:
        return source_ireqs[0]

    link_attrs = {
        attr: getattr(source_ireqs[0], attr) for attr in ("link", "original_link")
    }

    constraint = source_ireqs[0].constraint
    extras = set(source_ireqs[0].extras)
    # deepcopy the accumulator req so as to not modify the inputs
    req = copy.deepcopy(source_ireqs[0].req)

    for ireq in source_ireqs[1:]:
        # NOTE we may be losing some info on dropped reqs here
        if req is not None and ireq.req is not None:
            req.specifier &= ireq.req.specifier

        constraint &= ireq.constraint
        extras |= ireq.extras
        if req is not None:
            req.extras = set(extras)

        for attr_name, attr_val in link_attrs.items():
            link_attrs[attr_name] = attr_val or getattr(ireq, attr_name)

    # InstallRequirements objects are assumed to come from only one source, and
    # so they support only a single comes_from entry. This function breaks this
    # model. As a workaround, we deterministically choose a single source for
    # the comes_from entry, and add an extra _source_ireqs attribute to keep
    # track of multiple sources for use within pip-tools.
    if any(ireq.comes_from is None for ireq in source_ireqs):
        # None indicates package was directly specified.
        comes_from = None
    else:
        # Populate the comes_from field from one of the sources.
        # Requirement input order is not stable, so we need to sort:
        # We choose the shortest entry in order to keep the printed
        # representation as concise as possible.
        comes_from = min(
            (ireq.comes_from for ireq in source_ireqs),
            key=lambda x: (len(str(x)), str(x)),
        )

    combined_ireq = copy_install_requirement(
        template=source_ireqs[0],
        req=req,
        comes_from=comes_from,
        constraint=constraint,
        extras=extras,
        **link_attrs,
    )
    combined_ireq._source_ireqs = source_ireqs

    return combined_ireq


class BaseResolver(metaclass=ABCMeta):
    repository: BaseRepository
    unsafe_constraints: set[InstallRequirement]

    @abstractmethod
    def resolve(self, max_rounds: int) -> set[InstallRequirement]:
        """
        Find concrete package versions for all the given InstallRequirements
        and their recursive dependencies and return a set of pinned
        ``InstallRequirement``'s.
        """

    def resolve_hashes(
        self, ireqs: set[InstallRequirement]
    ) -> dict[InstallRequirement, set[str]]:
        """Find acceptable hashes for all of the given ``InstallRequirement``s."""
        log.debug("")
        log.debug("Generating hashes:")
        with self.repository.allow_all_wheels(), log.indentation():
            return {ireq: self.repository.get_hashes(ireq) for ireq in ireqs}

    def _filter_out_unsafe_constraints(
        self,
        ireqs: set[InstallRequirement],
        unsafe_packages: Container[str],
    ) -> None:
        """
        Remove from a given set of ``InstallRequirement``'s unsafe constraints.
        """
        for req in ireqs.copy():
            if req.name in unsafe_packages:
                self.unsafe_constraints.add(req)
                ireqs.remove(req)


class LegacyResolver(BaseResolver):
    def __init__(
        self,
        constraints: Iterable[InstallRequirement],
        existing_constraints: dict[str, InstallRequirement],
        repository: BaseRepository,
        cache: DependencyCache,
        prereleases: bool | None = False,
        clear_caches: bool = False,
        allow_unsafe: bool = False,
        unsafe_packages: set[str] | None = None,
    ) -> None:
        """
        This class resolves a given set of constraints (a collection of
        InstallRequirement objects) by consulting the given Repository and the
        DependencyCache.
        """
        self.our_constraints = set(constraints)
        self.their_constraints: set[InstallRequirement] = set()
        self.repository = repository
        self.dependency_cache = cache
        self.prereleases = prereleases
        self.clear_caches = clear_caches
        self.allow_unsafe = allow_unsafe
        self.unsafe_constraints: set[InstallRequirement] = set()
        self.unsafe_packages = unsafe_packages or UNSAFE_PACKAGES

        options = self.repository.options
        if "legacy-resolver" not in options.deprecated_features_enabled:
            raise PipToolsError("Legacy resolver deprecated feature must be enabled.")

        # Make sure there is no enabled 2020-resolver
        options.features_enabled = omit_list_value(
            options.features_enabled, "2020-resolver"
        )

    @property
    def constraints(self) -> set[InstallRequirement]:
        return set(
            self._group_constraints(chain(self.our_constraints, self.their_constraints))
        )

    def resolve(self, max_rounds: int = 10) -> set[InstallRequirement]:
        """
        Find concrete package versions for all the given InstallRequirements
        and their recursive dependencies and return a set of pinned
        ``InstallRequirement``'s.

        Resolves constraints one round at a time, until they don't change
        anymore.  Protects against infinite loops by breaking out after a max
        number rounds.
        """
        if self.clear_caches:
            self.dependency_cache.clear()
            self.repository.clear_caches()

        # Ignore existing packages
        with update_env_context_manager(PIP_EXISTS_ACTION="i"):
            for current_round in count(start=1):  # pragma: no branch
                if current_round > max_rounds:
                    raise RuntimeError(
                        "No stable configuration of concrete packages "
                        "could be found for the given constraints after "
                        "{max_rounds} rounds of resolving.\n"
                        "This is likely a bug.".format(max_rounds=max_rounds)
                    )

                log.debug("")
                log.debug(magenta(f"{f'ROUND {current_round}':^60}"))
                has_changed, best_matches = self._resolve_one_round()
                log.debug("-" * 60)
                log.debug(
                    "Result of round {}: {}".format(
                        current_round,
                        "not stable" if has_changed else "stable, done",
                    )
                )
                if not has_changed:
                    break

        # Only include hard requirements and not pip constraints
        results = {req for req in best_matches if not req.constraint}

        # Filter out unsafe requirements.
        if not self.allow_unsafe:
            self._filter_out_unsafe_constraints(
                ireqs=results,
                unsafe_packages=self.unsafe_packages,
            )

        return results

    def _group_constraints(
        self, constraints: Iterable[InstallRequirement]
    ) -> Iterator[InstallRequirement]:
        """
        Groups constraints (remember, InstallRequirements!) by their key name,
        and combining their SpecifierSets into a single InstallRequirement per
        package.  For example, given the following constraints:

            Django<1.9,>=1.4.2
            django~=1.5
            Flask~=0.7

        This will be combined into a single entry per package:

            django~=1.5,<1.9,>=1.4.2
            flask~=0.7

        """
        constraints = list(constraints)

        for ireq in constraints:
            if ireq.name is None:
                # get_dependencies has side-effect of assigning name to ireq
                # (so we can group by the name below).
                self.repository.get_dependencies(ireq)

        # Sort first by name, i.e. the groupby key. Then within each group,
        # sort editables first.
        # This way, we don't bother with combining editables, since the first
        # ireq will be editable, if one exists.
        for _, ireqs in groupby(
            sorted(constraints, key=(lambda x: (key_from_ireq(x), not x.editable))),
            key=key_from_ireq,
        ):
            yield combine_install_requirements(ireqs)

    def _resolve_one_round(self) -> tuple[bool, set[InstallRequirement]]:
        """
        Resolves one level of the current constraints, by finding the best
        match for each package in the repository and adding all requirements
        for those best package versions.  Some of these constraints may be new
        or updated.

        Returns whether new constraints appeared in this round.  If no
        constraints were added or changed, this indicates a stable
        configuration.
        """
        # Sort this list for readability of terminal output
        constraints = sorted(self.constraints, key=key_from_ireq)

        log.debug("Current constraints:")
        with log.indentation():
            for constraint in constraints:
                log.debug(str(constraint))

        log.debug("")
        log.debug("Finding the best candidates:")
        with log.indentation():
            best_matches = {self.get_best_match(ireq) for ireq in constraints}

        # Find the new set of secondary dependencies
        log.debug("")
        log.debug("Finding secondary dependencies:")

        their_constraints: list[InstallRequirement] = []
        with log.indentation():
            for best_match in best_matches:
                their_constraints.extend(self._iter_dependencies(best_match))
        # Grouping constraints to make clean diff between rounds
        theirs = set(self._group_constraints(their_constraints))

        # NOTE: We need to compare RequirementSummary objects, since
        # InstallRequirement does not define equality
        diff = {RequirementSummary(t) for t in theirs} - {
            RequirementSummary(t) for t in self.their_constraints
        }
        removed = {RequirementSummary(t) for t in self.their_constraints} - {
            RequirementSummary(t) for t in theirs
        }

        has_changed = len(diff) > 0 or len(removed) > 0
        if has_changed:
            log.debug("")
            log.debug("New dependencies found in this round:")
            with log.indentation():
                for new_dependency in sorted(diff, key=key_from_ireq):
                    log.debug(f"adding {new_dependency}")
            log.debug("Removed dependencies in this round:")
            with log.indentation():
                for removed_dependency in sorted(removed, key=key_from_ireq):
                    log.debug(f"removing {removed_dependency}")

        # Store the last round's results in the their_constraints
        self.their_constraints = theirs
        return has_changed, best_matches

    def get_best_match(self, ireq: InstallRequirement) -> InstallRequirement:
        """
        Returns a (pinned or editable) InstallRequirement, indicating the best
        match to use for the given InstallRequirement (in the form of an
        InstallRequirement).

        Example:
        Given the constraint Flask>=0.10, may return Flask==0.10.1 at
        a certain moment in time.

        Pinned requirements will always return themselves, i.e.

            Flask==0.10.1 => Flask==0.10.1

        """
        if ireq.editable or is_url_requirement(ireq):
            # NOTE: it's much quicker to immediately return instead of
            # hitting the index server
            best_match = ireq
        elif is_pinned_requirement(ireq):
            # NOTE: it's much quicker to immediately return instead of
            # hitting the index server
            best_match = ireq
        elif ireq.constraint:
            # NOTE: This is not a requirement (yet) and does not need
            # to be resolved
            best_match = ireq
        else:
            best_match = self.repository.find_best_match(
                ireq, prereleases=self.prereleases
            )

        # Format the best match
        log.debug(
            "found candidate {} (constraint was {})".format(
                format_requirement(best_match), format_specifier(ireq)
            )
        )
        best_match.comes_from = ireq.comes_from
        if hasattr(ireq, "_source_ireqs"):
            best_match._source_ireqs = ireq._source_ireqs
        return best_match

    def _iter_dependencies(
        self, ireq: InstallRequirement
    ) -> Iterator[InstallRequirement]:
        """
        Given a pinned, url, or editable InstallRequirement, collects all the
        secondary dependencies for them, either by looking them up in a local
        cache, or by reaching out to the repository.

        Editable requirements will never be looked up, as they may have
        changed at any time.
        """
        # Pip does not resolve dependencies of constraints. We skip handling
        # constraints here as well to prevent the cache from being polluted.
        # Constraints that are later determined to be dependencies will be
        # marked as non-constraints in later rounds by
        # `combine_install_requirements`, and will be properly resolved.
        # See https://github.com/pypa/pip/
        # blob/6896dfcd831330c13e076a74624d95fa55ff53f4/src/pip/_internal/
        # legacy_resolve.py#L325
        if ireq.constraint:
            return

        if ireq.editable or is_url_requirement(ireq):
            dependencies = self.repository.get_dependencies(ireq)
            # Don't just yield from above. Instead, use the same `markers`-stripping
            # behavior as we have for cached dependencies below.
            dependency_strings = sorted(str(ireq.req) for ireq in dependencies)
            yield from self._ireqs_of_dependencies(ireq, dependency_strings)
            return
        elif not is_pinned_requirement(ireq):
            raise TypeError(f"Expected pinned or editable requirement, got {ireq}")

        # Now, either get the dependencies from the dependency cache (for
        # speed), or reach out to the external repository to
        # download and inspect the package version and get dependencies
        # from there
        if ireq not in self.dependency_cache:
            log.debug(
                f"{format_requirement(ireq)} not in cache, need to check index",
                fg="yellow",
            )
            dependencies = self.repository.get_dependencies(ireq)
            self.dependency_cache[ireq] = sorted(str(ireq.req) for ireq in dependencies)

        # Example: ['Werkzeug>=0.9', 'Jinja2>=2.4']
        dependency_strings = self.dependency_cache[ireq]
        yield from self._ireqs_of_dependencies(ireq, dependency_strings)

    def _ireqs_of_dependencies(
        self, ireq: InstallRequirement, dependency_strings: list[str]
    ) -> Iterator[InstallRequirement]:
        log.debug(
            "{:25} requires {}".format(
                format_requirement(ireq),
                ", ".join(sorted(dependency_strings, key=lambda s: s.lower())) or "-",
            )
        )
        # This yields new InstallRequirements that are similar to those that
        # produced the dependency_strings, but they lack `markers` on their
        # underlying Requirements:
        for dependency_string in dependency_strings:
            yield install_req_from_line(
                dependency_string, constraint=ireq.constraint, comes_from=ireq
            )


class BacktrackingResolver(BaseResolver):
    """A wrapper for backtracking resolver."""

    def __init__(
        self,
        constraints: Iterable[InstallRequirement],
        existing_constraints: dict[str, InstallRequirement],
        repository: BaseRepository,
        allow_unsafe: bool = False,
        unsafe_packages: set[str] | None = None,
        **kwargs: Any,
    ) -> None:
        self.constraints = list(constraints)
        self.repository = repository
        self.allow_unsafe = allow_unsafe
        self.unsafe_packages = unsafe_packages or UNSAFE_PACKAGES

        options = self.options = self.repository.options
        self.session = self.repository.session
        self.finder = self.repository.finder
        self.command = self.repository.command
        self.unsafe_constraints: set[InstallRequirement] = set()

        self.existing_constraints = existing_constraints

        # Categorize InstallRequirements into sets by key
        constraints_sets: DefaultDict[str, set[InstallRequirement]] = (
            collections.defaultdict(set)
        )
        for ireq in constraints:
            constraints_sets[key_from_ireq(ireq)].add(ireq)
        # Collapse each set of InstallRequirements using combine_install_requirements
        self._constraints_map = {
            ireq_key: combine_install_requirements(ireqs)
            for ireq_key, ireqs in constraints_sets.items()
        }

        # Make sure there is no enabled legacy resolver
        options.deprecated_features_enabled = omit_list_value(
            options.deprecated_features_enabled, "legacy-resolver"
        )

    def resolve(self, max_rounds: int = 10) -> set[InstallRequirement]:
        """
        Find concrete package versions for all the given InstallRequirements
        and their recursive dependencies and return a set of pinned
        ``InstallRequirement``'s.
        """
        with update_env_context_manager(
            PIP_EXISTS_ACTION="i"
        ), get_build_tracker() as build_tracker, global_tempdir_manager(), indent_log():
            # Mark direct/primary/user_supplied packages
            for ireq in self.constraints:
                if ireq.constraint:
                    ireq.extras = set()  # pip does not support extras in constraints
                ireq.user_supplied = True

            # Pass compiled requirements from `requirements.txt`
            # as constraints to resolver
            compatible_existing_constraints: dict[str, InstallRequirement] = {}
            for ireq in self.existing_constraints.values():
                # Skip if the compiled install requirement conflicts with
                # the primary install requirement.
                primary_ireq = self._constraints_map.get(key_from_ireq(ireq))
                if primary_ireq is not None:
                    _, version, _ = as_tuple(ireq)
                    prereleases = ireq.specifier.prereleases
                    if not primary_ireq.specifier.contains(version, prereleases):
                        continue

                ireq.extras = set()
                ireq.constraint = True
                ireq.user_supplied = False
                compatible_existing_constraints[key_from_ireq(ireq)] = ireq

            wheel_cache = create_wheel_cache(
                cache_dir=self.options.cache_dir,
                format_control=self.options.format_control,
            )

            temp_dir = TempDirectory(
                delete=not self.options.no_clean,
                kind="resolve",
                globally_managed=True,
            )

            preparer_kwargs = {
                "temp_build_dir": temp_dir,
                "options": self.options,
                "session": self.session,
                "finder": self.finder,
                "use_user_site": False,
                "build_tracker": build_tracker,
            }
            preparer = self.command.make_requirement_preparer(**preparer_kwargs)

            resolver = self.command.make_resolver(
                preparer=preparer,
                finder=self.finder,
                options=self.options,
                wheel_cache=wheel_cache,
                use_user_site=False,
                ignore_installed=True,
                ignore_requires_python=False,
                force_reinstall=False,
                use_pep517=self.options.use_pep517,
                upgrade_strategy="to-satisfy-only",
            )

            self.command.trace_basic_info(self.finder)

            for current_round in count(start=1):  # pragma: no branch
                if current_round > max_rounds:
                    raise RuntimeError(
                        "No stable configuration of concrete packages "
                        "could be found for the given constraints after "
                        f"{max_rounds} rounds of resolving.\n"
                        "This is likely a bug."
                    )

                log.debug("")
                log.debug(magenta(f"{f'ROUND {current_round}':^60}"))

                is_resolved = self._do_resolve(
                    resolver=resolver,
                    compatible_existing_constraints=compatible_existing_constraints,
                )
                if is_resolved:
                    break

        resolver_result = resolver._result
        assert isinstance(resolver_result, Result)

        # Prepare set of install requirements from resolver result.
        result_ireqs = self._get_install_requirements(resolver_result=resolver_result)

        # Filter out unsafe requirements.
        if not self.allow_unsafe:
            self._filter_out_unsafe_constraints(
                ireqs=result_ireqs,
                unsafe_packages=self.unsafe_packages,
            )

        return result_ireqs

    def _do_resolve(
        self,
        resolver: Resolver,
        compatible_existing_constraints: dict[str, InstallRequirement],
    ) -> bool:
        """
        Return true on successful resolution, otherwise remove problematic
        requirements from existing constraints and return false.
        """
        try:
            resolver.resolve(
                root_reqs=self.constraints
                + list(compatible_existing_constraints.values()),
                check_supported_wheels=not self.options.target_dir,
            )
        except DistributionNotFound as e:
            cause_exc = e.__cause__
            if cause_exc is None:
                raise

            if not isinstance(cause_exc, ResolutionImpossible):
                raise

            # Collect all incompatible install requirement names
            cause_ireq_names = {
                strip_extras(key_from_req(cause.requirement))
                for cause in cause_exc.causes
            }

            # Looks like resolution is impossible, try to fix
            for cause_ireq_name in cause_ireq_names:
                # Find the cause requirement in existing requirements,
                # otherwise raise error
                cause_existing_ireq = compatible_existing_constraints.get(
                    cause_ireq_name
                )
                if cause_existing_ireq is None:
                    raise

                # Remove existing incompatible constraint that causes error
                log.warning(
                    f"Discarding {cause_existing_ireq} to proceed the resolution"
                )
                del compatible_existing_constraints[cause_ireq_name]

            return False

        return True

    def _get_install_requirements(
        self, resolver_result: Result
    ) -> set[InstallRequirement]:
        """Return a set of install requirements from resolver results."""
        result_ireqs: dict[str, InstallRequirement] = {}

        # Get reverse requirements from the resolver result graph.
        reverse_dependencies = self._get_reverse_dependencies(resolver_result)

        # Transform candidates to install requirements
        resolved_candidates = tuple(resolver_result.mapping.values())
        for candidate in resolved_candidates:
            ireq = self._get_install_requirement_from_candidate(
                candidate=candidate,
                reverse_dependencies=reverse_dependencies,
            )
            if ireq is None:
                continue

            project_name = canonicalize_name(candidate.project_name)
            result_ireqs[project_name] = ireq

        # Merge extras to install requirements
        extras_candidates = (
            candidate
            for candidate in resolved_candidates
            if isinstance(candidate, ExtrasCandidate)
        )
        for extras_candidate in extras_candidates:
            project_name = canonicalize_name(extras_candidate.project_name)
            ireq = result_ireqs[project_name]
            ireq.extras |= extras_candidate.extras
            ireq.req.extras |= extras_candidate.extras

        return set(result_ireqs.values())

    @staticmethod
    def _get_reverse_dependencies(
        resolver_result: Result,
    ) -> dict[str, set[str]]:
        reverse_dependencies: DefaultDict[str, set[str]] = collections.defaultdict(set)

        for candidate in resolver_result.mapping.values():
            stripped_name = strip_extras(canonicalize_name(candidate.name))

            for parent_name in resolver_result.graph.iter_parents(candidate.name):
                # Skip root dependency which is always None
                if parent_name is None:
                    continue

                # Skip a dependency that equals to the candidate. This could be
                # the dependency with extras.
                stripped_parent_name = strip_extras(canonicalize_name(parent_name))
                if stripped_name == stripped_parent_name:
                    continue

                reverse_dependencies[stripped_name].add(stripped_parent_name)

        return dict(reverse_dependencies)

    def _get_install_requirement_from_candidate(
        self, candidate: Candidate, reverse_dependencies: dict[str, set[str]]
    ) -> InstallRequirement | None:
        ireq = candidate.get_install_requirement()
        if ireq is None:
            return None

        # Determine a pin operator
        version_pin_operator = "=="
        version_as_str = str(candidate.version)
        for specifier in ireq.specifier:
            if specifier.operator == "===" and specifier.version == version_as_str:
                version_pin_operator = "==="
                break

        # Prepare pinned install requirement. Copy it from candidate's install
        # requirement so that it could be mutated later.
        pinned_ireq = copy_install_requirement(
            template=ireq,
            # The link this candidate "originates" from. This is different
            # from ``ireq.link`` when the link is found in the wheel cache.
            # ``ireq.link`` would point to the wheel cache, while this points
            # to the found remote link (e.g. from pypi.org).
            link=candidate.source_link,
        )

        # Canonicalize name
        assert ireq.name is not None
        pinned_ireq.req.name = canonicalize_name(ireq.name)

        # Pin requirement to a resolved version
        pinned_ireq.req.specifier = SpecifierSet(
            f"{version_pin_operator}{candidate.version}"
        )

        # Save reverse dependencies for annotation
        ireq_key = key_from_ireq(ireq)
        pinned_ireq._required_by = reverse_dependencies.get(ireq_key, set())

        # Save sources for annotation
        constraint_ireq = self._constraints_map.get(ireq_key)
        if constraint_ireq is not None:
            if hasattr(constraint_ireq, "_source_ireqs"):
                # If the constraint is combined (has _source_ireqs), use those
                pinned_ireq._source_ireqs = constraint_ireq._source_ireqs
            else:
                # Otherwise (the constraint is not combined) it is the source
                pinned_ireq._source_ireqs = [constraint_ireq]

        return pinned_ireq
