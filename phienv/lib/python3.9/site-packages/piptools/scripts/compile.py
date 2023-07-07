from __future__ import annotations

import itertools
import os
import shlex
import sys
import tempfile
from pathlib import Path
from typing import IO, Any, BinaryIO, cast

import click
from build import BuildBackendException
from build.util import project_wheel_metadata
from click.utils import LazyFile, safecall
from pip._internal.commands import create_command
from pip._internal.req import InstallRequirement
from pip._internal.req.constructors import install_req_from_line
from pip._internal.utils.misc import redact_auth_from_url

from .._compat import parse_requirements
from ..cache import DependencyCache
from ..exceptions import NoCandidateFound, PipToolsError
from ..locations import CACHE_DIR, CONFIG_FILE_NAME
from ..logging import log
from ..repositories import LocalRequirementsRepository, PyPIRepository
from ..repositories.base import BaseRepository
from ..resolver import BacktrackingResolver, LegacyResolver
from ..utils import (
    UNSAFE_PACKAGES,
    dedup,
    drop_extras,
    is_pinned_requirement,
    key_from_ireq,
    override_defaults_from_config_file,
    parse_requirements_from_wheel_metadata,
)
from ..writer import OutputWriter

DEFAULT_REQUIREMENTS_FILES = (
    "requirements.in",
    "setup.py",
    "pyproject.toml",
    "setup.cfg",
)
DEFAULT_REQUIREMENTS_OUTPUT_FILE = "requirements.txt"
METADATA_FILENAMES = frozenset({"setup.py", "setup.cfg", "pyproject.toml"})


def _get_default_option(option_name: str) -> Any:
    """
    Get default value of the pip's option (including option from pip.conf)
    by a given option name.
    """
    install_command = create_command("install")
    default_values = install_command.parser.get_default_values()
    return getattr(default_values, option_name)


def _determine_linesep(
    strategy: str = "preserve", filenames: tuple[str, ...] = ()
) -> str:
    """
    Determine and return linesep string for OutputWriter to use.
    Valid strategies: "LF", "CRLF", "native", "preserve"
    When preserving, files are checked in order for existing newlines.
    """
    if strategy == "preserve":
        for fname in filenames:
            try:
                with open(fname, "rb") as existing_file:
                    existing_text = existing_file.read()
            except FileNotFoundError:
                continue
            if b"\r\n" in existing_text:
                strategy = "CRLF"
                break
            elif b"\n" in existing_text:
                strategy = "LF"
                break
    return {
        "native": os.linesep,
        "LF": "\n",
        "CRLF": "\r\n",
        "preserve": "\n",
    }[strategy]


@click.command(context_settings={"help_option_names": ("-h", "--help")})
@click.version_option(package_name="pip-tools")
@click.pass_context
@click.option("-v", "--verbose", count=True, help="Show more output")
@click.option("-q", "--quiet", count=True, help="Give less output")
@click.option(
    "-n",
    "--dry-run",
    is_flag=True,
    help="Only show what would happen, don't change anything",
)
@click.option(
    "-p",
    "--pre",
    is_flag=True,
    default=None,
    help="Allow resolving to prereleases (default is not)",
)
@click.option(
    "-r",
    "--rebuild",
    is_flag=True,
    help="Clear any caches upfront, rebuild from scratch",
)
@click.option(
    "--extra",
    "extras",
    multiple=True,
    help="Name of an extras_require group to install; may be used more than once",
)
@click.option(
    "--all-extras",
    is_flag=True,
    default=False,
    help="Install all extras_require groups",
)
@click.option(
    "-f",
    "--find-links",
    multiple=True,
    help="Look for archives in this directory or on this HTML page; may be used more than once",
)
@click.option(
    "-i",
    "--index-url",
    help="Change index URL (defaults to {index_url})".format(
        index_url=redact_auth_from_url(_get_default_option("index_url"))
    ),
)
@click.option(
    "--no-index",
    is_flag=True,
    help="Ignore package index (only looking at --find-links URLs instead).",
)
@click.option(
    "--extra-index-url",
    multiple=True,
    help="Add another index URL to search; may be used more than once",
)
@click.option("--cert", help="Path to alternate CA bundle.")
@click.option(
    "--client-cert",
    help="Path to SSL client certificate, a single file containing "
    "the private key and the certificate in PEM format.",
)
@click.option(
    "--trusted-host",
    multiple=True,
    help="Mark this host as trusted, even though it does not have "
    "valid or any HTTPS; may be used more than once",
)
@click.option(
    "--header/--no-header",
    is_flag=True,
    default=True,
    help="Add header to generated file",
)
@click.option(
    "--emit-trusted-host/--no-emit-trusted-host",
    is_flag=True,
    default=True,
    help="Add trusted host option to generated file",
)
@click.option(
    "--annotate/--no-annotate",
    is_flag=True,
    default=True,
    help="Annotate results, indicating where dependencies come from",
)
@click.option(
    "--annotation-style",
    type=click.Choice(("line", "split")),
    default="split",
    help="Choose the format of annotation comments",
)
@click.option(
    "-U",
    "--upgrade/--no-upgrade",
    is_flag=True,
    default=False,
    help="Try to upgrade all dependencies to their latest versions",
)
@click.option(
    "-P",
    "--upgrade-package",
    "upgrade_packages",
    nargs=1,
    multiple=True,
    help="Specify a particular package to upgrade; may be used more than once",
)
@click.option(
    "-o",
    "--output-file",
    nargs=1,
    default=None,
    type=click.File("w+b", atomic=True, lazy=True),
    help=(
        "Output file name. Required if more than one input file is given. "
        "Will be derived from input file otherwise."
    ),
)
@click.option(
    "--newline",
    type=click.Choice(("LF", "CRLF", "native", "preserve"), case_sensitive=False),
    default="preserve",
    help="Override the newline control characters used",
)
@click.option(
    "--allow-unsafe/--no-allow-unsafe",
    is_flag=True,
    default=False,
    help=(
        "Pin packages considered unsafe: {}.\n\n"
        "WARNING: Future versions of pip-tools will enable this behavior by default. "
        "Use --no-allow-unsafe to keep the old behavior. It is recommended to pass the "
        "--allow-unsafe now to adapt to the upcoming change.".format(
            ", ".join(sorted(UNSAFE_PACKAGES))
        )
    ),
)
@click.option(
    "--strip-extras",
    is_flag=True,
    default=False,
    help="Assure output file is constraints compatible, avoiding use of extras.",
)
@click.option(
    "--generate-hashes",
    is_flag=True,
    default=False,
    help="Generate pip 8 style hashes in the resulting requirements file.",
)
@click.option(
    "--reuse-hashes/--no-reuse-hashes",
    is_flag=True,
    default=True,
    help=(
        "Improve the speed of --generate-hashes by reusing the hashes from an "
        "existing output file."
    ),
)
@click.option(
    "--max-rounds",
    default=10,
    help="Maximum number of rounds before resolving the requirements aborts.",
)
@click.argument("src_files", nargs=-1, type=click.Path(exists=True, allow_dash=True))
@click.option(
    "--build-isolation/--no-build-isolation",
    is_flag=True,
    default=True,
    help="Enable isolation when building a modern source distribution. "
    "Build dependencies specified by PEP 518 must be already installed "
    "if build isolation is disabled.",
)
@click.option(
    "--emit-find-links/--no-emit-find-links",
    is_flag=True,
    default=True,
    help="Add the find-links option to generated file",
)
@click.option(
    "--cache-dir",
    help="Store the cache data in DIRECTORY.",
    default=CACHE_DIR,
    envvar="PIP_TOOLS_CACHE_DIR",
    show_default=True,
    show_envvar=True,
    type=click.Path(file_okay=False, writable=True),
)
@click.option(
    "--pip-args", "pip_args_str", help="Arguments to pass directly to the pip command."
)
@click.option(
    "--resolver",
    "resolver_name",
    type=click.Choice(("legacy", "backtracking")),
    default="legacy",
    envvar="PIP_TOOLS_RESOLVER",
    help="Choose the dependency resolver.",
)
@click.option(
    "--emit-index-url/--no-emit-index-url",
    is_flag=True,
    default=True,
    help="Add index URL to generated file",
)
@click.option(
    "--emit-options/--no-emit-options",
    is_flag=True,
    default=True,
    help="Add options to generated file",
)
@click.option(
    "--unsafe-package",
    multiple=True,
    help="Specify a package to consider unsafe; may be used more than once. "
    f"Replaces default unsafe packages: {', '.join(sorted(UNSAFE_PACKAGES))}",
)
@click.option(
    "--config",
    type=click.Path(
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        allow_dash=False,
        path_type=str,
    ),
    help=f"Read configuration from TOML file. By default, looks for a {CONFIG_FILE_NAME} or "
    "pyproject.toml.",
    is_eager=True,
    callback=override_defaults_from_config_file,
)
def cli(
    ctx: click.Context,
    verbose: int,
    quiet: int,
    dry_run: bool,
    pre: bool,
    rebuild: bool,
    extras: tuple[str, ...],
    all_extras: bool,
    find_links: tuple[str, ...],
    index_url: str,
    no_index: bool,
    extra_index_url: tuple[str, ...],
    cert: str | None,
    client_cert: str | None,
    trusted_host: tuple[str, ...],
    header: bool,
    emit_trusted_host: bool,
    annotate: bool,
    annotation_style: str,
    upgrade: bool,
    upgrade_packages: tuple[str, ...],
    output_file: LazyFile | IO[Any] | None,
    newline: str,
    allow_unsafe: bool,
    strip_extras: bool,
    generate_hashes: bool,
    reuse_hashes: bool,
    src_files: tuple[str, ...],
    max_rounds: int,
    build_isolation: bool,
    emit_find_links: bool,
    cache_dir: str,
    pip_args_str: str | None,
    resolver_name: str,
    emit_index_url: bool,
    emit_options: bool,
    unsafe_package: tuple[str, ...],
    config: Path | None,
) -> None:
    """
    Compiles requirements.txt from requirements.in, pyproject.toml, setup.cfg,
    or setup.py specs.
    """
    log.verbosity = verbose - quiet

    if len(src_files) == 0:
        for file_path in DEFAULT_REQUIREMENTS_FILES:
            if os.path.exists(file_path):
                src_files = (file_path,)
                break
        else:
            raise click.BadParameter(
                (
                    "If you do not specify an input file, the default is one of: {}"
                ).format(", ".join(DEFAULT_REQUIREMENTS_FILES))
            )

    if not output_file:
        # An output file must be provided for stdin
        if src_files == ("-",):
            raise click.BadParameter("--output-file is required if input is from stdin")
        # Use default requirements output file if there is a setup.py the source file
        elif os.path.basename(src_files[0]) in METADATA_FILENAMES:
            file_name = os.path.join(
                os.path.dirname(src_files[0]), DEFAULT_REQUIREMENTS_OUTPUT_FILE
            )
        # An output file must be provided if there are multiple source files
        elif len(src_files) > 1:
            raise click.BadParameter(
                "--output-file is required if two or more input files are given."
            )
        # Otherwise derive the output file from the source file
        else:
            base_name = src_files[0].rsplit(".", 1)[0]
            file_name = base_name + ".txt"

        output_file = click.open_file(file_name, "w+b", atomic=True, lazy=True)

        # Close the file at the end of the context execution
        assert output_file is not None
        # only LazyFile has close_intelligently, newer IO[Any] does not
        if isinstance(output_file, LazyFile):  # pragma: no cover
            ctx.call_on_close(safecall(output_file.close_intelligently))

    if output_file.name != "-" and output_file.name in src_files:
        raise click.BadArgumentUsage(
            f"input and output filenames must not be matched: {output_file.name}"
        )

    if config:
        log.debug(f"Using pip-tools configuration defaults found in '{config !s}'.")

    if resolver_name == "legacy":
        log.warning(
            "WARNING: the legacy dependency resolver is deprecated and will be removed"
            " in future versions of pip-tools. The default resolver will be changed to"
            " 'backtracking' in pip-tools 7.0.0. Specify --resolver=backtracking to"
            " silence this warning."
        )

    ###
    # Setup
    ###

    right_args = shlex.split(pip_args_str or "")
    pip_args = []
    for link in find_links:
        pip_args.extend(["-f", link])
    if index_url:
        pip_args.extend(["-i", index_url])
    if no_index:
        pip_args.extend(["--no-index"])
    for extra_index in extra_index_url:
        pip_args.extend(["--extra-index-url", extra_index])
    if cert:
        pip_args.extend(["--cert", cert])
    if client_cert:
        pip_args.extend(["--client-cert", client_cert])
    if pre:
        pip_args.extend(["--pre"])
    for host in trusted_host:
        pip_args.extend(["--trusted-host", host])
    if not build_isolation:
        pip_args.append("--no-build-isolation")
    if resolver_name == "legacy":
        pip_args.extend(["--use-deprecated", "legacy-resolver"])
    if resolver_name == "backtracking" and cache_dir:
        pip_args.extend(["--cache-dir", cache_dir])
    pip_args.extend(right_args)

    repository: BaseRepository
    repository = PyPIRepository(pip_args, cache_dir=cache_dir)

    # Parse all constraints coming from --upgrade-package/-P
    upgrade_reqs_gen = (install_req_from_line(pkg) for pkg in upgrade_packages)
    upgrade_install_reqs = {
        key_from_ireq(install_req): install_req for install_req in upgrade_reqs_gen
    }

    # Exclude packages from --upgrade-package/-P from the existing constraints
    existing_pins = {}

    # Proxy with a LocalRequirementsRepository if --upgrade is not specified
    # (= default invocation)
    output_file_exists = os.path.exists(output_file.name)
    if not upgrade and output_file_exists:
        output_file_is_empty = os.path.getsize(output_file.name) == 0
        if upgrade_install_reqs and output_file_is_empty:
            log.warning(
                f"WARNING: the output file {output_file.name} exists but is empty. "
                "Pip-tools cannot upgrade only specific packages (using -P/--upgrade-package) "
                "without an existing pin file to provide constraints. "
                "This often occurs if you redirect standard output to your output file, "
                "as any existing content is truncated."
            )

        # Use a temporary repository to ensure outdated(removed) options from
        # existing requirements.txt wouldn't get into the current repository.
        tmp_repository = PyPIRepository(pip_args, cache_dir=cache_dir)
        ireqs = parse_requirements(
            output_file.name,
            finder=tmp_repository.finder,
            session=tmp_repository.session,
            options=tmp_repository.options,
        )

        for ireq in filter(is_pinned_requirement, ireqs):
            key = key_from_ireq(ireq)
            if key not in upgrade_install_reqs:
                existing_pins[key] = ireq
        repository = LocalRequirementsRepository(
            existing_pins, repository, reuse_hashes=reuse_hashes
        )

    ###
    # Parsing/collecting initial requirements
    ###

    constraints: list[InstallRequirement] = []
    setup_file_found = False
    for src_file in src_files:
        is_setup_file = os.path.basename(src_file) in METADATA_FILENAMES
        if src_file == "-":
            # pip requires filenames and not files. Since we want to support
            # piping from stdin, we need to briefly save the input from stdin
            # to a temporary file and have pip read that.  also used for
            # reading requirements from install_requires in setup.py.
            tmpfile = tempfile.NamedTemporaryFile(mode="wt", delete=False)
            tmpfile.write(sys.stdin.read())
            comes_from = "-r -"
            tmpfile.flush()
            reqs = list(
                parse_requirements(
                    tmpfile.name,
                    finder=repository.finder,
                    session=repository.session,
                    options=repository.options,
                )
            )
            for req in reqs:
                req.comes_from = comes_from
            constraints.extend(reqs)
        elif is_setup_file:
            setup_file_found = True
            try:
                metadata = project_wheel_metadata(
                    os.path.dirname(os.path.abspath(src_file)),
                    isolated=build_isolation,
                )
            except BuildBackendException as e:
                log.error(str(e))
                log.error(f"Failed to parse {os.path.abspath(src_file)}")
                sys.exit(2)

            constraints.extend(
                parse_requirements_from_wheel_metadata(
                    metadata=metadata, src_file=src_file
                )
            )

            if all_extras:
                if extras:
                    msg = "--extra has no effect when used with --all-extras"
                    raise click.BadParameter(msg)
                extras = tuple(metadata.get_all("Provides-Extra"))
        else:
            constraints.extend(
                parse_requirements(
                    src_file,
                    finder=repository.finder,
                    session=repository.session,
                    options=repository.options,
                )
            )

    if upgrade_packages:
        constraints_file = tempfile.NamedTemporaryFile(mode="wt", delete=False)
        constraints_file.write("\n".join(upgrade_packages))
        constraints_file.flush()
        try:
            reqs = list(
                parse_requirements(
                    constraints_file.name,
                    finder=repository.finder,
                    session=repository.session,
                    options=repository.options,
                    constraint=True,
                )
            )
        finally:
            constraints_file.close()
            os.unlink(constraints_file.name)
        for req in reqs:
            req.comes_from = None
        constraints.extend(reqs)

    extras = tuple(itertools.chain.from_iterable(ex.split(",") for ex in extras))

    if extras and not setup_file_found:
        msg = "--extra has effect only with setup.py and PEP-517 input formats"
        raise click.BadParameter(msg)

    primary_packages = {
        key_from_ireq(ireq) for ireq in constraints if not ireq.constraint
    }

    constraints.extend(
        ireq for key, ireq in upgrade_install_reqs.items() if key in primary_packages
    )

    constraints = [req for req in constraints if req.match_markers(extras)]
    for req in constraints:
        drop_extras(req)

    if repository.finder.index_urls:
        log.debug("Using indexes:")
        with log.indentation():
            for index_url in dedup(repository.finder.index_urls):
                log.debug(redact_auth_from_url(index_url))
    else:
        log.debug("Ignoring indexes.")

    if repository.finder.find_links:
        log.debug("")
        log.debug("Using links:")
        with log.indentation():
            for find_link in dedup(repository.finder.find_links):
                log.debug(redact_auth_from_url(find_link))

    resolver_cls = LegacyResolver if resolver_name == "legacy" else BacktrackingResolver
    try:
        resolver = resolver_cls(
            constraints=constraints,
            existing_constraints=existing_pins,
            repository=repository,
            prereleases=repository.finder.allow_all_prereleases or pre,
            cache=DependencyCache(cache_dir),
            clear_caches=rebuild,
            allow_unsafe=allow_unsafe,
            unsafe_packages=set(unsafe_package),
        )
        results = resolver.resolve(max_rounds=max_rounds)
        hashes = resolver.resolve_hashes(results) if generate_hashes else None
    except NoCandidateFound as e:
        if resolver_cls == LegacyResolver:  # pragma: no branch
            log.error(
                "Using legacy resolver. "
                "Consider using backtracking resolver with "
                "`--resolver=backtracking`."
            )

        log.error(str(e))
        sys.exit(2)
    except PipToolsError as e:
        log.error(str(e))
        sys.exit(2)

    log.debug("")

    linesep = _determine_linesep(
        strategy=newline, filenames=(output_file.name, *src_files)
    )

    ##
    # Output
    ##

    writer = OutputWriter(
        cast(BinaryIO, output_file),
        click_ctx=ctx,
        dry_run=dry_run,
        emit_header=header,
        emit_index_url=emit_index_url,
        emit_trusted_host=emit_trusted_host,
        annotate=annotate,
        annotation_style=annotation_style,
        strip_extras=strip_extras,
        generate_hashes=generate_hashes,
        default_index_url=repository.DEFAULT_INDEX_URL,
        index_urls=repository.finder.index_urls,
        trusted_hosts=repository.finder.trusted_hosts,
        format_control=repository.finder.format_control,
        linesep=linesep,
        allow_unsafe=allow_unsafe,
        find_links=repository.finder.find_links,
        emit_find_links=emit_find_links,
        emit_options=emit_options,
    )
    writer.write(
        results=results,
        unsafe_packages=resolver.unsafe_packages,
        unsafe_requirements=resolver.unsafe_constraints,
        markers={
            key_from_ireq(ireq): ireq.markers for ireq in constraints if ireq.markers
        },
        hashes=hashes,
    )

    if dry_run:
        log.info("Dry-run, so nothing updated.")
