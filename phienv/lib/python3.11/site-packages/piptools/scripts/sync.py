from __future__ import annotations

import itertools
import os
import shlex
import shutil
import sys
from pathlib import Path
from typing import cast

import click
from pip._internal.commands import create_command
from pip._internal.commands.install import InstallCommand
from pip._internal.index.package_finder import PackageFinder
from pip._internal.metadata import get_environment

from .. import sync
from .._compat import Distribution, parse_requirements
from ..exceptions import PipToolsError
from ..logging import log
from ..repositories import PyPIRepository
from ..utils import (
    flat_map,
    get_pip_version_for_python_executable,
    get_required_pip_specification,
    get_sys_path_for_python_executable,
)
from . import options

DEFAULT_REQUIREMENTS_FILE = "requirements.txt"


@click.command(
    name="pip-sync", context_settings={"help_option_names": options.help_option_names}
)
@options.version
@options.ask
@options.dry_run
@options.force
@options.find_links
@options.index_url
@options.extra_index_url
@options.trusted_host
@options.no_index
@options.python_executable
@options.verbose
@options.quiet
@options.user
@options.cert
@options.client_cert
@options.src_files
@options.pip_args
@options.config
@options.no_config
def cli(
    ask: bool,
    dry_run: bool,
    force: bool,
    find_links: tuple[str, ...],
    index_url: str | None,
    extra_index_url: tuple[str, ...],
    trusted_host: tuple[str, ...],
    no_index: bool,
    python_executable: str | None,
    verbose: int,
    quiet: int,
    user_only: bool,
    cert: str | None,
    client_cert: str | None,
    src_files: tuple[str, ...],
    pip_args_str: str | None,
    config: Path | None,
    no_config: bool,
) -> None:
    """Synchronize virtual environment with requirements.txt."""
    log.verbosity = verbose - quiet

    if not src_files:
        if os.path.exists(DEFAULT_REQUIREMENTS_FILE):
            src_files = (DEFAULT_REQUIREMENTS_FILE,)
        else:
            msg = "No requirement files given and no {} found in the current directory"
            log.error(msg.format(DEFAULT_REQUIREMENTS_FILE))
            sys.exit(2)

    if any(src_file.endswith(".in") for src_file in src_files):
        msg = (
            "Some input files have the .in extension, which is most likely an error "
            "and can cause weird behaviour. You probably meant to use "
            "the corresponding *.txt file?"
        )
        if force:
            log.warning("WARNING: " + msg)
        else:
            log.error("ERROR: " + msg)
            sys.exit(2)

    if config:
        log.debug(f"Using pip-tools configuration defaults found in '{config !s}'.")

    if python_executable:
        _validate_python_executable(python_executable)

    install_command = cast(InstallCommand, create_command("install"))
    options, _ = install_command.parse_args([])
    session = install_command._build_session(options)
    finder = install_command._build_package_finder(options=options, session=session)

    # Parse requirements file. Note, all options inside requirements file
    # will be collected by the finder.
    requirements = flat_map(
        lambda src: parse_requirements(src, finder=finder, session=session), src_files
    )

    try:
        merged_requirements = sync.merge(requirements, ignore_conflicts=force)
    except PipToolsError as e:
        log.error(str(e))
        sys.exit(2)

    paths = (
        None
        if python_executable is None
        else get_sys_path_for_python_executable(python_executable)
    )
    installed_dists = _get_installed_distributions(
        user_only=user_only,
        local_only=python_executable is None,
        paths=paths,
    )
    to_install, to_uninstall = sync.diff(merged_requirements, installed_dists)

    install_flags = _compose_install_flags(
        finder,
        no_index=no_index,
        index_url=index_url,
        extra_index_url=extra_index_url,
        trusted_host=trusted_host,
        find_links=find_links,
        user_only=user_only,
        cert=cert,
        client_cert=client_cert,
    ) + shlex.split(pip_args_str or "")
    sys.exit(
        sync.sync(
            to_install,
            to_uninstall,
            dry_run=dry_run,
            install_flags=install_flags,
            ask=ask,
            python_executable=python_executable,
        )
    )


def _validate_python_executable(python_executable: str) -> None:
    """
    Validates incoming python_executable argument passed to CLI.
    """
    resolved_python_executable = shutil.which(python_executable)
    if resolved_python_executable is None:
        msg = "Could not resolve '{}' as valid executable path or alias."
        log.error(msg.format(python_executable))
        sys.exit(2)

    # Ensure that target python executable has the right version of pip installed
    pip_version = get_pip_version_for_python_executable(python_executable)
    required_pip_specification = get_required_pip_specification()
    if not required_pip_specification.contains(pip_version, prereleases=True):
        msg = (
            "Target python executable '{}' has pip version {} installed. "
            "Version {} is expected."
        )
        log.error(
            msg.format(python_executable, pip_version, required_pip_specification)
        )
        sys.exit(2)


def _compose_install_flags(
    finder: PackageFinder,
    no_index: bool,
    index_url: str | None,
    extra_index_url: tuple[str, ...],
    trusted_host: tuple[str, ...],
    find_links: tuple[str, ...],
    user_only: bool,
    cert: str | None,
    client_cert: str | None,
) -> list[str]:
    """
    Compose install flags with the given finder and CLI options.
    """
    result = []

    # Build --index-url/--extra-index-url/--no-index
    if no_index:
        result.append("--no-index")
    elif index_url is not None:
        result.extend(["--index-url", index_url])
    elif finder.index_urls:
        finder_index_url = finder.index_urls[0]
        if finder_index_url != PyPIRepository.DEFAULT_INDEX_URL:
            result.extend(["--index-url", finder_index_url])
        for extra_index in finder.index_urls[1:]:
            result.extend(["--extra-index-url", extra_index])
    else:
        result.append("--no-index")

    for extra_index in extra_index_url:
        result.extend(["--extra-index-url", extra_index])

    # Build --trusted-hosts
    for host in itertools.chain(trusted_host, finder.trusted_hosts):
        result.extend(["--trusted-host", host])

    # Build --find-links
    for link in itertools.chain(find_links, finder.find_links):
        result.extend(["--find-links", link])

    # Build format controls --no-binary/--only-binary
    for format_control in ("no_binary", "only_binary"):
        formats = getattr(finder.format_control, format_control)
        if not formats:
            continue
        result.extend(
            ["--" + format_control.replace("_", "-"), ",".join(sorted(formats))]
        )

    if user_only:
        result.append("--user")

    if cert is not None:
        result.extend(["--cert", cert])

    if client_cert is not None:
        result.extend(["--client-cert", client_cert])

    return result


def _get_installed_distributions(
    local_only: bool = True,
    user_only: bool = False,
    paths: list[str] | None = None,
) -> list[Distribution]:
    """Return a list of installed Distribution objects."""

    env = get_environment(paths)
    dists = env.iter_installed_distributions(
        local_only=local_only,
        user_only=user_only,
        skip=[],
    )
    return [Distribution.from_pip_distribution(dist) for dist in dists]
