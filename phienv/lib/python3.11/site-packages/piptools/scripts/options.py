from __future__ import annotations

from typing import Any, Literal

import click
from pip._internal.commands import create_command
from pip._internal.utils.misc import redact_auth_from_url

from piptools.locations import CACHE_DIR, DEFAULT_CONFIG_FILE_NAMES
from piptools.utils import UNSAFE_PACKAGES, override_defaults_from_config_file

BuildTargetT = Literal["sdist", "wheel", "editable"]
ALL_BUILD_TARGETS: tuple[BuildTargetT, ...] = (
    "editable",
    "sdist",
    "wheel",
)


def _get_default_option(option_name: str) -> Any:
    """
    Get default value of the pip's option (including option from pip.conf)
    by a given option name.
    """
    install_command = create_command("install")
    default_values = install_command.parser.get_default_values()
    return getattr(default_values, option_name)


help_option_names = ("-h", "--help")

# The options used by pip-compile and pip-sync are presented in no specific order.

version = click.version_option(package_name="pip-tools")

color = click.option(
    "--color/--no-color",
    default=None,
    help="Force output to be colorized or not, instead of auto-detecting color support",
)

verbose = click.option(
    "-v",
    "--verbose",
    count=True,
    help="Show more output",
)
quiet = click.option(
    "-q",
    "--quiet",
    count=True,
    help="Give less output",
)

dry_run = click.option(
    "-n",
    "--dry-run",
    is_flag=True,
    help="Only show what would happen, don't change anything",
)

pre = click.option(
    "-p",
    "--pre",
    is_flag=True,
    default=None,
    help="Allow resolving to prereleases (default is not)",
)

rebuild = click.option(
    "-r",
    "--rebuild",
    is_flag=True,
    help="Clear any caches upfront, rebuild from scratch",
)

extra = click.option(
    "--extra",
    "extras",
    multiple=True,
    help="Name of an extras_require group to install; may be used more than once",
)

all_extras = click.option(
    "--all-extras",
    is_flag=True,
    default=False,
    help="Install all extras_require groups",
)

find_links = click.option(
    "-f",
    "--find-links",
    multiple=True,
    help="Look for archives in this directory or on this HTML page; may be used more than once",
)

index_url = click.option(
    "-i",
    "--index-url",
    help="Change index URL (defaults to {index_url})".format(
        index_url=redact_auth_from_url(_get_default_option("index_url"))
    ),
)

no_index = click.option(
    "--no-index",
    is_flag=True,
    help="Ignore package index (only looking at --find-links URLs instead).",
)

extra_index_url = click.option(
    "--extra-index-url",
    multiple=True,
    help="Add another index URL to search; may be used more than once",
)

cert = click.option("--cert", help="Path to alternate CA bundle.")

client_cert = click.option(
    "--client-cert",
    help=(
        "Path to SSL client certificate, a single file containing "
        "the private key and the certificate in PEM format."
    ),
)

trusted_host = click.option(
    "--trusted-host",
    multiple=True,
    help=(
        "Mark this host as trusted, even though it does not have "
        "valid or any HTTPS; may be used more than once"
    ),
)

header = click.option(
    "--header/--no-header",
    is_flag=True,
    default=True,
    help="Add header to generated file",
)

emit_trusted_host = click.option(
    "--emit-trusted-host/--no-emit-trusted-host",
    is_flag=True,
    default=True,
    help="Add trusted host option to generated file",
)

annotate = click.option(
    "--annotate/--no-annotate",
    is_flag=True,
    default=True,
    help="Annotate results, indicating where dependencies come from",
)

annotation_style = click.option(
    "--annotation-style",
    type=click.Choice(("line", "split")),
    default="split",
    help="Choose the format of annotation comments",
)

upgrade = click.option(
    "-U",
    "--upgrade/--no-upgrade",
    is_flag=True,
    default=False,
    help="Try to upgrade all dependencies to their latest versions",
)

upgrade_package = click.option(
    "-P",
    "--upgrade-package",
    "upgrade_packages",
    nargs=1,
    multiple=True,
    help="Specify a particular package to upgrade; may be used more than once",
)

output_file = click.option(
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

newline = click.option(
    "--newline",
    type=click.Choice(("LF", "CRLF", "native", "preserve"), case_sensitive=False),
    default="preserve",
    help="Override the newline control characters used",
)

allow_unsafe = click.option(
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

strip_extras = click.option(
    "--strip-extras/--no-strip-extras",
    is_flag=True,
    default=None,
    help="Assure output file is constraints compatible, avoiding use of extras.",
)

generate_hashes = click.option(
    "--generate-hashes",
    is_flag=True,
    default=False,
    help="Generate pip 8 style hashes in the resulting requirements file.",
)

reuse_hashes = click.option(
    "--reuse-hashes/--no-reuse-hashes",
    is_flag=True,
    default=True,
    help=(
        "Improve the speed of --generate-hashes by reusing the hashes from an "
        "existing output file."
    ),
)

max_rounds = click.option(
    "--max-rounds",
    default=10,
    help="Maximum number of rounds before resolving the requirements aborts.",
)

src_files = click.argument(
    "src_files",
    nargs=-1,
    type=click.Path(exists=True, allow_dash=True),
)

build_isolation = click.option(
    "--build-isolation/--no-build-isolation",
    is_flag=True,
    default=True,
    help=(
        "Enable isolation when building a modern source distribution. "
        "Build dependencies specified by PEP 518 must be already installed "
        "if build isolation is disabled."
    ),
)

emit_find_links = click.option(
    "--emit-find-links/--no-emit-find-links",
    is_flag=True,
    default=True,
    help="Add the find-links option to generated file",
)

cache_dir = click.option(
    "--cache-dir",
    help="Store the cache data in DIRECTORY.",
    default=CACHE_DIR,
    envvar="PIP_TOOLS_CACHE_DIR",
    show_default=True,
    show_envvar=True,
    type=click.Path(file_okay=False, writable=True),
)

pip_args = click.option(
    "--pip-args",
    "pip_args_str",
    help="Arguments to pass directly to the pip command.",
)

resolver = click.option(
    "--resolver",
    "resolver_name",
    type=click.Choice(("legacy", "backtracking")),
    default="backtracking",
    envvar="PIP_TOOLS_RESOLVER",
    help="Choose the dependency resolver.",
)

emit_index_url = click.option(
    "--emit-index-url/--no-emit-index-url",
    is_flag=True,
    default=True,
    help="Add index URL to generated file",
)

emit_options = click.option(
    "--emit-options/--no-emit-options",
    is_flag=True,
    default=True,
    help="Add options to generated file",
)

unsafe_package = click.option(
    "--unsafe-package",
    multiple=True,
    help=(
        "Specify a package to consider unsafe; may be used more than once. "
        f"Replaces default unsafe packages: {', '.join(sorted(UNSAFE_PACKAGES))}"
    ),
)

config = click.option(
    "--config",
    type=click.Path(
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        allow_dash=False,
        path_type=str,
    ),
    help=(
        f"Read configuration from TOML file. By default, looks for the following "
        f"files in the given order: {', '.join(DEFAULT_CONFIG_FILE_NAMES)}."
    ),
    is_eager=True,
    callback=override_defaults_from_config_file,
)

no_config = click.option(
    "--no-config",
    is_flag=True,
    default=False,
    help="Do not read any config file.",
    is_eager=True,
)

constraint = click.option(
    "-c",
    "--constraint",
    multiple=True,
    help="Constrain versions using the given constraints file; may be used more than once.",
)

ask = click.option(
    "-a",
    "--ask",
    is_flag=True,
    help="Show what would happen, then ask whether to continue",
)

force = click.option(
    "--force", is_flag=True, help="Proceed even if conflicts are found"
)

python_executable = click.option(
    "--python-executable",
    help="Custom python executable path if targeting an environment other than current.",
)

user = click.option(
    "--user",
    "user_only",
    is_flag=True,
    help="Restrict attention to user directory",
)

build_deps_for = click.option(
    "--build-deps-for",
    "build_deps_targets",
    multiple=True,
    type=click.Choice(ALL_BUILD_TARGETS),
    help="Name of a build target to extract dependencies for. "
    "Static dependencies declared in 'pyproject.toml::build-system.requires' will be included as "
    "well; may be used more than once.",
)

all_build_deps = click.option(
    "--all-build-deps",
    is_flag=True,
    default=False,
    help="Extract dependencies for all build targets. "
    "Static dependencies declared in 'pyproject.toml::build-system.requires' will be included as "
    "well.",
)

only_build_deps = click.option(
    "--only-build-deps",
    is_flag=True,
    default=False,
    help="Extract a package only if it is a build dependency.",
)
