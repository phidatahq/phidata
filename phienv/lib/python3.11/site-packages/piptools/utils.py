from __future__ import annotations

import collections
import copy
import difflib
import itertools
import json
import os
import re
import shlex
import sys
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator, TypeVar, cast

from click.core import ParameterSource

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

import click
from click.utils import LazyFile
from pip._internal.req import InstallRequirement
from pip._internal.req.constructors import install_req_from_line
from pip._internal.resolution.resolvelib.base import Requirement as PipRequirement
from pip._internal.utils.misc import redact_auth_from_url
from pip._internal.vcs import is_url
from pip._vendor.packaging.markers import Marker
from pip._vendor.packaging.requirements import Requirement
from pip._vendor.packaging.specifiers import SpecifierSet
from pip._vendor.packaging.utils import canonicalize_name
from pip._vendor.packaging.version import Version
from pip._vendor.pkg_resources import get_distribution

from piptools._compat import PIP_VERSION
from piptools.locations import DEFAULT_CONFIG_FILE_NAMES
from piptools.subprocess_utils import run_python_snippet

_KT = TypeVar("_KT")
_VT = TypeVar("_VT")
_T = TypeVar("_T")
_S = TypeVar("_S")

UNSAFE_PACKAGES = {"setuptools", "distribute", "pip"}
COMPILE_EXCLUDE_OPTIONS = {
    "--dry-run",
    "--quiet",
    "--rebuild",
    "--upgrade",
    "--upgrade-package",
    "--verbose",
    "--cache-dir",
    "--no-reuse-hashes",
    "--no-config",
}

# Set of option that are only negative, i.e. --no-<option>
ONLY_NEGATIVE_OPTIONS = {"--no-index"}


def key_from_ireq(ireq: InstallRequirement) -> str:
    """Get a standardized key for an InstallRequirement."""
    if ireq.req is None and ireq.link is not None:
        return str(ireq.link)
    else:
        return key_from_req(ireq.req)


def key_from_req(req: InstallRequirement | Requirement | PipRequirement) -> str:
    """
    Get an all-lowercase version of the requirement's name.

    **Note:** If the argument is an instance of
    ``pip._internal.resolution.resolvelib.base.Requirement`` (like
    ``pip._internal.resolution.resolvelib.requirements.SpecifierRequirement``),
    then the name might include an extras specification.
    Apply :py:func:`strip_extras` to the result of this function if you need
    the package name only.

    :param req: the requirement the key is computed for
    :return: the canonical name of the requirement
    """
    return str(canonicalize_name(req.name))


def comment(text: str) -> str:
    return click.style(text, fg="green")


def make_install_requirement(
    name: str, version: str | Version, ireq: InstallRequirement
) -> InstallRequirement:
    # If no extras are specified, the extras string is blank
    extras_string = ""
    extras = ireq.extras
    if extras:
        # Sort extras for stability
        extras_string = f"[{','.join(sorted(extras))}]"

    version_pin_operator = "=="
    version_as_str = str(version)
    for specifier in ireq.specifier:
        if specifier.operator == "===" and specifier.version == version_as_str:
            version_pin_operator = "==="
            break

    return install_req_from_line(
        str(f"{name}{extras_string}{version_pin_operator}{version}"),
        constraint=ireq.constraint,
    )


def is_url_requirement(ireq: InstallRequirement) -> bool:
    """
    Return True if requirement was specified as a path or URL.
    ireq.original_link will have been set by InstallRequirement.__init__
    """
    return bool(ireq.original_link)


def format_requirement(
    ireq: InstallRequirement,
    marker: Marker | None = None,
    hashes: set[str] | None = None,
) -> str:
    """
    Generic formatter for pretty printing InstallRequirements to the terminal
    in a less verbose way than using its `__str__` method.
    """
    if ireq.editable:
        line = f"-e {ireq.link.url}"
    elif is_url_requirement(ireq):
        line = _build_direct_reference_best_efforts(ireq)
    else:
        # Canonicalize the requirement name
        # https://packaging.pypa.io/en/latest/utils.html#packaging.utils.canonicalize_name
        req = copy.copy(ireq.req)
        req.name = canonicalize_name(req.name)
        line = str(req)

    if marker:
        line = f"{line} ; {marker}"

    if hashes:
        for hash_ in sorted(hashes):
            line += f" \\\n    --hash={hash_}"

    return line


def _build_direct_reference_best_efforts(ireq: InstallRequirement) -> str:
    """
    Returns a string of a direct reference URI, whenever possible.
    See https://www.python.org/dev/peps/pep-0508/
    """
    # If the requirement has no name then we cannot build a direct reference.
    if not ireq.name:
        return cast(str, ireq.link.url)

    # Look for a relative file path, the direct reference currently does not work with it.
    if ireq.link.is_file and not ireq.link.path.startswith("/"):
        return cast(str, ireq.link.url)

    # If we get here then we have a requirement that supports direct reference.
    # We need to remove the egg if it exists and keep the rest of the fragments.
    lowered_ireq_name = canonicalize_name(ireq.name)
    extras = f"[{','.join(sorted(ireq.extras))}]" if ireq.extras else ""
    direct_reference = f"{lowered_ireq_name}{extras} @ {ireq.link.url_without_fragment}"
    fragments = []

    # Check if there is any fragment to add to the URI.
    if ireq.link.subdirectory_fragment:
        fragments.append(f"subdirectory={ireq.link.subdirectory_fragment}")

    if ireq.link.has_hash:
        fragments.append(f"{ireq.link.hash_name}={ireq.link.hash}")

    # Then add the fragments into the URI, if any.
    if fragments:
        direct_reference += f"#{'&'.join(fragments)}"

    return direct_reference


def format_specifier(ireq: InstallRequirement) -> str:
    """
    Generic formatter for pretty printing the specifier part of
    InstallRequirements to the terminal.
    """
    # TODO: Ideally, this is carried over to the pip library itself
    specs = ireq.specifier if ireq.req is not None else SpecifierSet()
    # FIXME: remove ignore type marker once the following issue get fixed
    #        https://github.com/python/mypy/issues/9656
    specs = sorted(specs, key=lambda x: x.version)
    return ",".join(str(s) for s in specs) or "<any>"


def is_pinned_requirement(ireq: InstallRequirement) -> bool:
    """
    Returns whether an InstallRequirement is a "pinned" requirement.

    An InstallRequirement is considered pinned if:

    - Is not editable
    - It has exactly one specifier
    - That specifier is "=="
    - The version does not contain a wildcard

    Examples:
        django==1.8   # pinned
        django>1.8    # NOT pinned
        django~=1.8   # NOT pinned
        django==1.*   # NOT pinned
    """
    if ireq.editable:
        return False

    if ireq.req is None or len(ireq.specifier) != 1:
        return False

    spec = next(iter(ireq.specifier))
    return spec.operator in {"==", "==="} and not spec.version.endswith(".*")


def as_tuple(ireq: InstallRequirement) -> tuple[str, str, tuple[str, ...]]:
    """
    Pulls out the (name: str, version:str, extras:(str)) tuple from
    the pinned InstallRequirement.
    """
    if not is_pinned_requirement(ireq):
        raise TypeError(f"Expected a pinned InstallRequirement, got {ireq}")

    name = key_from_ireq(ireq)
    version = next(iter(ireq.specifier)).version
    extras = tuple(sorted(ireq.extras))
    return name, version, extras


def flat_map(
    fn: Callable[[_T], Iterable[_S]], collection: Iterable[_T]
) -> Iterator[_S]:
    """Map a function over a collection and flatten the result by one-level"""
    return itertools.chain.from_iterable(map(fn, collection))


def lookup_table_from_tuples(values: Iterable[tuple[_KT, _VT]]) -> dict[_KT, set[_VT]]:
    """
    Builds a dict-based lookup table (index) elegantly.
    """
    lut: dict[_KT, set[_VT]] = collections.defaultdict(set)
    for k, v in values:
        lut[k].add(v)
    return dict(lut)


def lookup_table(
    values: Iterable[_VT], key: Callable[[_VT], _KT]
) -> dict[_KT, set[_VT]]:
    """
    Builds a dict-based lookup table (index) elegantly.
    """
    return lookup_table_from_tuples((key(v), v) for v in values)


def dedup(iterable: Iterable[_T]) -> Iterable[_T]:
    """Deduplicate an iterable object like iter(set(iterable)) but
    order-preserved.
    """
    return iter(dict.fromkeys(iterable))


def drop_extras(ireq: InstallRequirement) -> None:
    """Remove "extra" markers (PEP-508) from requirement."""
    if ireq.markers is None:
        return
    ireq.markers._markers = _drop_extras(ireq.markers._markers)
    if not ireq.markers._markers:
        ireq.markers = None


def _drop_extras(markers: list[_T]) -> list[_T]:
    # drop `extra` tokens
    to_remove: list[int] = []
    for i, token in enumerate(markers):
        # operator (and/or)
        if isinstance(token, str):
            continue
        # sub-expression (inside braces)
        if isinstance(token, list):
            markers[i] = _drop_extras(token)  # type: ignore
            if markers[i]:
                continue
            to_remove.append(i)
            continue
        # test expression (like `extra == "dev"`)
        assert isinstance(token, tuple)
        if token[0].value == "extra":
            to_remove.append(i)
    for i in reversed(to_remove):
        markers.pop(i)

    # drop duplicate bool operators (and/or)
    to_remove = []
    for i, (token1, token2) in enumerate(zip(markers, markers[1:])):
        if not isinstance(token1, str):
            continue
        if not isinstance(token2, str):
            continue
        if token1 == "and":
            to_remove.append(i)
        else:
            to_remove.append(i + 1)
    for i in reversed(to_remove):
        markers.pop(i)
    if markers and isinstance(markers[0], str):
        markers.pop(0)
    if markers and isinstance(markers[-1], str):
        markers.pop(-1)

    return markers


def get_hashes_from_ireq(ireq: InstallRequirement) -> set[str]:
    """
    Given an InstallRequirement, return a set of string hashes in the format
    "{algorithm}:{hash}". Return an empty set if there are no hashes in the
    requirement options.
    """
    result = set()
    for algorithm, hexdigests in ireq.hash_options.items():
        for hash_ in hexdigests:
            result.add(f"{algorithm}:{hash_}")
    return result


def get_compile_command(click_ctx: click.Context) -> str:
    """
    Returns a normalized compile command depending on cli context.

    The command will be normalized by:
        - expanding options short to long
        - removing values that are already default
        - sorting the arguments
        - removing one-off arguments like '--upgrade'
        - removing arguments that don't change build behaviour like '--verbose'
    """
    from piptools.scripts.compile import cli

    # Map of the compile cli options (option name -> click.Option)
    compile_options = {option.name: option for option in cli.params}

    left_args = []
    right_args = []

    for option_name, value in click_ctx.params.items():
        option = compile_options[option_name]

        # Collect variadic args separately, they will be added
        # at the end of the command later
        if option.nargs < 0:
            # These will necessarily be src_files
            # Re-add click-stripped '--' if any start with '-'
            if any(val.startswith("-") and val != "-" for val in value):
                right_args.append("--")
            right_args.extend([shlex.quote(val) for val in value])
            continue

        assert isinstance(option, click.Option)

        # Get the latest option name (usually it'll be a long name)
        option_long_name = option.opts[-1]

        # Exclude one-off options (--upgrade/--upgrade-package/--rebuild/...)
        # or options that don't change compile behaviour (--verbose/--dry-run/...)
        if option_long_name in COMPILE_EXCLUDE_OPTIONS:
            continue

        # Exclude config option if it's the default one
        if option_long_name == "--config":
            parameter_source = click_ctx.get_parameter_source(option_name)
            if (
                str(value) in DEFAULT_CONFIG_FILE_NAMES
                or parameter_source == ParameterSource.DEFAULT
            ):
                continue

        # Skip options without a value
        if option.default is None and not value:
            continue

        # Skip options with a default value
        if option.default == value:
            continue

        # Use a file name for file-like objects
        if isinstance(value, LazyFile):
            value = value.name

        # Convert value to the list
        if not isinstance(value, (tuple, list)):
            value = [value]

        for val in value:
            # Flags don't have a value, thus add to args true or false option long name
            if option.is_flag:
                # If there are false-options, choose an option name depending on a value
                if option.secondary_opts:
                    # Get the latest false-option
                    secondary_option_long_name = option.secondary_opts[-1]
                    arg = option_long_name if val else secondary_option_long_name
                # There are no false-options, use true-option
                else:
                    arg = option_long_name
                left_args.append(shlex.quote(arg))
            # Append to args the option with a value
            else:
                if isinstance(val, str) and is_url(val):
                    val = redact_auth_from_url(val)
                if option.name == "pip_args_str":
                    # shlex.quote() would produce functional but noisily quoted results,
                    # e.g. --pip-args='--cache-dir='"'"'/tmp/with spaces'"'"''
                    # Instead, we try to get more legible quoting via repr:
                    left_args.append(f"{option_long_name}={repr(val)}")
                else:
                    left_args.append(f"{option_long_name}={shlex.quote(str(val))}")

    return " ".join(["pip-compile", *sorted(left_args), *sorted(right_args)])


def get_required_pip_specification() -> SpecifierSet:
    """
    Returns pip version specifier requested by current pip-tools installation.
    """
    project_dist = get_distribution("pip-tools")
    requirement = next(
        (r for r in project_dist.requires() if r.name == "pip"), None
    )  # pragma: no branch
    assert (
        requirement is not None
    ), "'pip' is expected to be in the list of pip-tools requirements"
    return requirement.specifier


def get_pip_version_for_python_executable(python_executable: str) -> Version:
    """
    Returns pip version for the given python executable.
    """
    str_version = run_python_snippet(
        python_executable, "import pip;print(pip.__version__)"
    )
    return Version(str_version)


def get_sys_path_for_python_executable(python_executable: str) -> list[str]:
    """
    Returns sys.path list for the given python executable.
    """
    result = run_python_snippet(
        python_executable, "import sys;import json;print(json.dumps(sys.path))"
    )

    paths = json.loads(result)
    assert isinstance(paths, list)
    assert all(isinstance(i, str) for i in paths)
    return [os.path.abspath(path) for path in paths]


def omit_list_value(lst: list[_T], value: _T) -> list[_T]:
    """Produce a new list with a given value skipped."""
    return [item for item in lst if item != value]


_strip_extras_re = re.compile(r"\[.+?\]")


def strip_extras(name: str) -> str:
    """Strip extras from package name, e.g. pytest[testing] -> pytest."""
    return re.sub(_strip_extras_re, "", name)


def copy_install_requirement(
    template: InstallRequirement, **extra_kwargs: Any
) -> InstallRequirement:
    """Make a copy of a template ``InstallRequirement`` with extra kwargs."""
    # Prepare install requirement kwargs.
    kwargs = {
        "comes_from": template.comes_from,
        "editable": template.editable,
        "link": template.link,
        "markers": template.markers,
        "use_pep517": template.use_pep517,
        "isolated": template.isolated,
        "global_options": template.global_options,
        "hash_options": template.hash_options,
        "constraint": template.constraint,
        "extras": template.extras,
        "user_supplied": template.user_supplied,
    }
    kwargs.update(extra_kwargs)

    if PIP_VERSION[:2] <= (23, 0):
        kwargs["install_options"] = template.install_options

    # Original link does not belong to install requirements constructor,
    # pop it now to update later.
    original_link = kwargs.pop("original_link", None)

    # Copy template.req if not specified in extra kwargs.
    if "req" not in kwargs:
        kwargs["req"] = copy.deepcopy(template.req)

    ireq = InstallRequirement(**kwargs)

    # If the original_link was None, keep it so. Passing `link` as an
    # argument to `InstallRequirement` sets it as the original_link.
    ireq.original_link = (
        template.original_link if original_link is None else original_link
    )

    return ireq


def override_defaults_from_config_file(
    ctx: click.Context, param: click.Parameter, value: str | None
) -> Path | None:
    """
    Overrides ``click.Command`` defaults based on specified or discovered config
    file, returning the ``pathlib.Path`` of that config file if specified or
    discovered.

    ``None`` is returned if no such file is found.

    ``pip-tools`` will use the first config file found, searching in this order:
    an explicitly given config file, a ``.pip-tools.toml``, a ``pyproject.toml``
    file. Those files are searched for in the same directory as the requirements
    input file, or the current working directory if requirements come via stdin.
    """
    if ctx.params.get("no_config"):
        return None

    if value is None:
        config_file = select_config_file(ctx.params.get("src_files", ()))
        if config_file is None:
            return None
    else:
        config_file = Path(value)

    config = parse_config_file(ctx, config_file)

    _validate_config(ctx, config)
    _assign_config_to_cli_context(ctx, config)

    return config_file


def _assign_config_to_cli_context(
    click_context: click.Context,
    cli_config_mapping: dict[str, Any],
) -> None:
    if click_context.default_map is None:
        click_context.default_map = {}

    click_context.default_map.update(cli_config_mapping)


def _validate_config(
    click_context: click.Context,
    config: dict[str, Any],
) -> None:
    """
    Validate parsed config against click command params.

    :raises click.NoSuchOption: if config contains unknown keys.
    :raises click.BadOptionUsage: if config contains invalid values.
    """
    from piptools.scripts.compile import cli as compile_cli
    from piptools.scripts.sync import cli as sync_cli

    compile_cli_params = {
        param.name: param for param in compile_cli.params if param.name is not None
    }

    sync_cli_params = {
        param.name: param for param in sync_cli.params if param.name is not None
    }

    all_keys = set(compile_cli_params) | set(sync_cli_params)

    for key, value in config.items():
        # Validate unknown keys in both compile and sync
        if key not in all_keys:
            possibilities = difflib.get_close_matches(key, all_keys)
            raise click.NoSuchOption(
                option_name=key,
                message=f"No such config key {key!r}.",
                possibilities=possibilities,
                ctx=click_context,
            )

        # Get all params associated with this key in both compile and sync
        associated_params = (
            cli_params[key]
            for cli_params in (compile_cli_params, sync_cli_params)
            if key in cli_params
        )

        # Validate value against types of all associated params
        for param in associated_params:
            try:
                param.type_cast_value(value=value, ctx=click_context)
            except Exception as e:
                raise click.BadOptionUsage(
                    option_name=key,
                    message=(
                        f"Invalid value for config key {key!r}: {value!r}.{os.linesep}"
                        f"Details: {e}"
                    ),
                    ctx=click_context,
                ) from e


def select_config_file(src_files: tuple[str, ...]) -> Path | None:
    """
    Returns the config file to use for defaults given ``src_files`` provided.
    """
    # NOTE: If no src_files were specified, consider the current directory the
    # NOTE: only config file lookup candidate. This usually happens when a
    # NOTE: pip-tools invocation gets its incoming requirements from standard
    # NOTE: input.
    working_directory = Path.cwd()
    src_files_as_paths = (
        (working_directory / src_file).resolve() for src_file in src_files or (".",)
    )
    candidate_dirs = (src if src.is_dir() else src.parent for src in src_files_as_paths)
    config_file_path = next(
        (
            candidate_dir / config_file
            for candidate_dir in candidate_dirs
            for config_file in DEFAULT_CONFIG_FILE_NAMES
            if (candidate_dir / config_file).is_file()
        ),
        None,
    )
    if config_file_path is None:
        return None

    return (
        config_file_path.relative_to(working_directory)
        if is_path_relative_to(config_file_path, working_directory)
        else config_file_path
    )


def get_cli_options(ctx: click.Context) -> dict[str, click.Parameter]:
    cli_opts = {
        opt: option
        for option in ctx.command.params
        for opt in itertools.chain(option.opts, option.secondary_opts)
        if opt.startswith("--") and option.name is not None
    }
    return cli_opts


def parse_config_file(
    click_context: click.Context, config_file: Path
) -> dict[str, Any]:
    try:
        config = tomllib.loads(config_file.read_text(encoding="utf-8"))
    except OSError as os_err:
        raise click.FileError(
            filename=str(config_file),
            hint=f"Could not read '{config_file !s}': {os_err !s}",
        )
    except ValueError as value_err:
        raise click.FileError(
            filename=str(config_file),
            hint=f"Could not parse '{config_file !s}': {value_err !s}",
        )

    # In a TOML file, we expect the config to be under `[tool.pip-tools]`,
    # `[tool.pip-tools.compile]` or `[tool.pip-tools.sync]`
    piptools_config: dict[str, Any] = config.get("tool", {}).get("pip-tools", {})

    assert click_context.command.name is not None
    # TODO: Replace with `str.removeprefix()` once dropped 3.8
    config_section_name = click_context.command.name[len("pip-") :]

    piptools_config.update(piptools_config.pop(config_section_name, {}))
    piptools_config.pop("compile", {})
    piptools_config.pop("sync", {})

    piptools_config = _normalize_keys_in_config(piptools_config)
    piptools_config = _invert_negative_bool_options_in_config(
        ctx=click_context,
        config=piptools_config,
    )

    return piptools_config


def _normalize_keys_in_config(config: dict[str, Any]) -> dict[str, Any]:
    return {_normalize_config_key(key): value for key, value in config.items()}


def _invert_negative_bool_options_in_config(
    ctx: click.Context, config: dict[str, Any]
) -> dict[str, Any]:
    new_config = {}
    cli_opts = get_cli_options(ctx)

    for key, value in config.items():
        # Transform config key to its equivalent in the CLI
        long_option = _convert_to_long_option(key)
        new_key = cli_opts[long_option].name if long_option in cli_opts else key
        negative_option_prefix = "no_"
        assert new_key is not None
        if (
            new_key.startswith(negative_option_prefix)
            and long_option not in ONLY_NEGATIVE_OPTIONS
        ):
            new_key = new_key[len(negative_option_prefix) :]

        # Invert negative boolean according to the CLI
        new_value = (
            not value
            if long_option.startswith("--no-")
            and long_option not in ONLY_NEGATIVE_OPTIONS
            and isinstance(value, bool)
            else value
        )
        new_config[new_key] = new_value

    return new_config


def _normalize_config_key(key: str) -> str:
    """Transform given ``some-key`` into ``some_key``."""
    return key.lstrip("-").replace("-", "_").lower()


def _convert_to_long_option(key: str) -> str:
    """Transform given ``some-key`` into ``--some-key``."""
    return "--" + key.lstrip("-").replace("_", "-").lower()


def is_path_relative_to(path1: Path, path2: Path) -> bool:
    """Return True if ``path1`` is relative to ``path2``."""
    # TODO: remove this function in favor of Path.is_relative_to()
    #       when we drop support for Python 3.8
    try:
        path1.relative_to(path2)
    except ValueError:
        return False
    return True
