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
from click.utils import LazyFile, safecall
from pip._internal.req import InstallRequirement
from pip._internal.req.constructors import install_req_from_line
from pip._internal.utils.misc import redact_auth_from_url

from .._compat import parse_requirements
from ..build import build_project_metadata
from ..cache import DependencyCache
from ..exceptions import NoCandidateFound, PipToolsError
from ..logging import log
from ..repositories import LocalRequirementsRepository, PyPIRepository
from ..repositories.base import BaseRepository
from ..resolver import BacktrackingResolver, LegacyResolver
from ..utils import dedup, drop_extras, is_pinned_requirement, key_from_ireq
from ..writer import OutputWriter
from . import options
from .options import BuildTargetT

DEFAULT_REQUIREMENTS_FILES = (
    "requirements.in",
    "setup.py",
    "pyproject.toml",
    "setup.cfg",
)
DEFAULT_REQUIREMENTS_FILE = "requirements.in"
DEFAULT_REQUIREMENTS_OUTPUT_FILE = "requirements.txt"
METADATA_FILENAMES = frozenset({"setup.py", "setup.cfg", "pyproject.toml"})


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


@click.command(
    name="pip-compile",
    context_settings={"help_option_names": options.help_option_names},
)
@click.pass_context
@options.version
@options.color
@options.verbose
@options.quiet
@options.dry_run
@options.pre
@options.rebuild
@options.extra
@options.all_extras
@options.find_links
@options.index_url
@options.no_index
@options.extra_index_url
@options.cert
@options.client_cert
@options.trusted_host
@options.header
@options.emit_trusted_host
@options.annotate
@options.annotation_style
@options.upgrade
@options.upgrade_package
@options.output_file
@options.newline
@options.allow_unsafe
@options.strip_extras
@options.generate_hashes
@options.reuse_hashes
@options.max_rounds
@options.src_files
@options.build_isolation
@options.emit_find_links
@options.cache_dir
@options.pip_args
@options.resolver
@options.emit_index_url
@options.emit_options
@options.unsafe_package
@options.config
@options.no_config
@options.constraint
@options.build_deps_for
@options.all_build_deps
@options.only_build_deps
def cli(
    ctx: click.Context,
    color: bool | None,
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
    strip_extras: bool | None,
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
    no_config: bool,
    constraint: tuple[str, ...],
    build_deps_targets: tuple[BuildTargetT, ...],
    all_build_deps: bool,
    only_build_deps: bool,
) -> None:
    """
    Compiles requirements.txt from requirements.in, pyproject.toml, setup.cfg,
    or setup.py specs.
    """
    if color is not None:
        ctx.color = color
    log.verbosity = verbose - quiet

    # If ``src-files` was not provided as an input, but rather as config,
    # it will be part of the click context ``ctx``.
    # However, if ``src_files`` is specified, then we want to use that.
    if not src_files and ctx.default_map and "src_files" in ctx.default_map:
        src_files = ctx.default_map["src_files"]

    if all_build_deps and build_deps_targets:
        raise click.BadParameter(
            "--build-deps-for has no effect when used with --all-build-deps"
        )
    elif all_build_deps:
        build_deps_targets = options.ALL_BUILD_TARGETS

    if only_build_deps and not build_deps_targets:
        raise click.BadParameter(
            "--only-build-deps requires either --build-deps-for or --all-build-deps"
        )
    if only_build_deps and (extras or all_extras):
        raise click.BadParameter(
            "--only-build-deps cannot be used with any of --extra, --all-extras"
        )

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

    if all_extras and extras:
        msg = "--extra has no effect when used with --all-extras"
        raise click.BadParameter(msg)

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
            " in future versions of pip-tools."
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
        if not is_setup_file and build_deps_targets:
            msg = (
                "--build-deps-for and --all-build-deps can be used only with the "
                "setup.py, setup.cfg and pyproject.toml specs."
            )
            raise click.BadParameter(msg)

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
                metadata = build_project_metadata(
                    src_file=Path(src_file),
                    build_targets=build_deps_targets,
                    isolated=build_isolation,
                    quiet=log.verbosity <= 0,
                )
            except BuildBackendException as e:
                log.error(str(e))
                log.error(f"Failed to parse {os.path.abspath(src_file)}")
                sys.exit(2)

            if not only_build_deps:
                constraints.extend(metadata.requirements)
                if all_extras:
                    extras += metadata.extras
            if build_deps_targets:
                constraints.extend(metadata.build_requirements)
        else:
            constraints.extend(
                parse_requirements(
                    src_file,
                    finder=repository.finder,
                    session=repository.session,
                    options=repository.options,
                )
            )

    # Parse all constraints from `--constraint` files
    for filename in constraint:
        constraints.extend(
            parse_requirements(
                filename,
                constraint=True,
                finder=repository.finder,
                options=repository.options,
                session=repository.session,
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

    if strip_extras is None:
        strip_extras = False
        log.warning(
            "WARNING: --strip-extras is becoming the default "
            "in version 8.0.0. To silence this warning, "
            "either use --strip-extras to opt into the new default "
            "or use --no-strip-extras to retain the existing behavior."
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
