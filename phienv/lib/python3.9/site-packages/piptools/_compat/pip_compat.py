from __future__ import annotations

import optparse
from typing import Callable, Iterable, Iterator, cast

import pip
from pip._internal.cache import WheelCache
from pip._internal.index.package_finder import PackageFinder
from pip._internal.network.session import PipSession
from pip._internal.req import InstallRequirement
from pip._internal.req import parse_requirements as _parse_requirements
from pip._internal.req.constructors import install_req_from_parsed_requirement
from pip._vendor.packaging.version import parse as parse_version
from pip._vendor.pkg_resources import Requirement

PIP_VERSION = tuple(map(int, parse_version(pip.__version__).base_version.split(".")))

__all__ = [
    "dist_requires",
    "uses_pkg_resources",
    "Distribution",
]


def parse_requirements(
    filename: str,
    session: PipSession,
    finder: PackageFinder | None = None,
    options: optparse.Values | None = None,
    constraint: bool = False,
    isolated: bool = False,
) -> Iterator[InstallRequirement]:
    for parsed_req in _parse_requirements(
        filename, session, finder=finder, options=options, constraint=constraint
    ):
        yield install_req_from_parsed_requirement(parsed_req, isolated=isolated)


# The Distribution interface has changed between pkg_resources and
# importlib.metadata, so this compat layer allows for a consistent access
# pattern. In pip 22.1, importlib.metadata became the default on Python 3.11
# (and later), but is overridable. `select_backend` returns what's being used.


def _uses_pkg_resources() -> bool:
    from pip._internal.metadata import select_backend
    from pip._internal.metadata.pkg_resources import Distribution as _Dist

    return select_backend().Distribution is _Dist


uses_pkg_resources = _uses_pkg_resources()

if uses_pkg_resources:
    from operator import methodcaller

    from pip._vendor.pkg_resources import Distribution

    dist_requires = cast(
        Callable[[Distribution], Iterable[Requirement]], methodcaller("requires")
    )
else:
    from pip._internal.metadata import select_backend

    Distribution = select_backend().Distribution

    def dist_requires(dist: Distribution) -> Iterable[Requirement]:
        """Mimics pkg_resources.Distribution.requires for the case of no
        extras. This doesn't fulfill that API's `extras` parameter but
        satisfies the needs of pip-tools."""
        reqs = (Requirement.parse(req) for req in (dist.requires or ()))
        return [
            req
            for req in reqs
            if not req.marker or req.marker.evaluate({"extra": None})
        ]


def create_wheel_cache(cache_dir: str, format_control: str | None = None) -> WheelCache:
    kwargs: dict[str, str | None] = {"cache_dir": cache_dir}
    if PIP_VERSION[:2] <= (23, 0):
        kwargs["format_control"] = format_control
    return WheelCache(**kwargs)
