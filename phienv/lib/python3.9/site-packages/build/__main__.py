# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse
import contextlib
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import textwrap
import traceback
import warnings

from collections.abc import Iterator, Sequence
from typing import NoReturn, TextIO

import build

from build import BuildBackendException, BuildException, ConfigSettingsType, FailedProcessError, PathType, ProjectBuilder
from build.env import IsolatedEnvBuilder


_COLORS = {
    'red': '\33[91m',
    'green': '\33[92m',
    'yellow': '\33[93m',
    'bold': '\33[1m',
    'dim': '\33[2m',
    'underline': '\33[4m',
    'reset': '\33[0m',
}
_NO_COLORS = {color: '' for color in _COLORS}


def _init_colors() -> dict[str, str]:
    if 'NO_COLOR' in os.environ:
        if 'FORCE_COLOR' in os.environ:
            warnings.warn('Both NO_COLOR and FORCE_COLOR environment variables are set, disabling color')
        return _NO_COLORS
    elif 'FORCE_COLOR' in os.environ or sys.stdout.isatty():
        return _COLORS
    return _NO_COLORS


_STYLES = _init_colors()


def _cprint(fmt: str = '', msg: str = '') -> None:
    print(fmt.format(msg, **_STYLES), flush=True)


def _showwarning(
    message: Warning | str,
    category: type[Warning],
    filename: str,
    lineno: int,
    file: TextIO | None = None,
    line: str | None = None,
) -> None:  # pragma: no cover
    _cprint('{yellow}WARNING{reset} {}', str(message))


def _setup_cli() -> None:
    warnings.showwarning = _showwarning

    if platform.system() == 'Windows':
        try:
            import colorama

            colorama.init()
        except ModuleNotFoundError:
            pass


def _error(msg: str, code: int = 1) -> NoReturn:  # pragma: no cover
    """
    Print an error message and exit. Will color the output when writing to a TTY.

    :param msg: Error message
    :param code: Error code
    """
    _cprint('{red}ERROR{reset} {}', msg)
    raise SystemExit(code)


class _ProjectBuilder(ProjectBuilder):
    @staticmethod
    def log(message: str) -> None:
        _cprint('{bold}* {}{reset}', message)


class _IsolatedEnvBuilder(IsolatedEnvBuilder):
    @staticmethod
    def log(message: str) -> None:
        _cprint('{bold}* {}{reset}', message)


def _format_dep_chain(dep_chain: Sequence[str]) -> str:
    return ' -> '.join(dep.partition(';')[0].strip() for dep in dep_chain)


def _build_in_isolated_env(
    builder: ProjectBuilder, outdir: PathType, distribution: str, config_settings: ConfigSettingsType | None
) -> str:
    with _IsolatedEnvBuilder() as env:
        builder.python_executable = env.executable
        builder.scripts_dir = env.scripts_dir
        # first install the build dependencies
        env.install(builder.build_system_requires)
        # then get the extra required dependencies from the backend (which was installed in the call above :P)
        env.install(builder.get_requires_for_build(distribution))
        return builder.build(distribution, outdir, config_settings or {})


def _build_in_current_env(
    builder: ProjectBuilder,
    outdir: PathType,
    distribution: str,
    config_settings: ConfigSettingsType | None,
    skip_dependency_check: bool = False,
) -> str:
    if not skip_dependency_check:
        missing = builder.check_dependencies(distribution)
        if missing:
            dependencies = ''.join('\n\t' + dep for deps in missing for dep in (deps[0], _format_dep_chain(deps[1:])) if dep)
            _cprint()
            _error(f'Missing dependencies:{dependencies}')

    return builder.build(distribution, outdir, config_settings or {})


def _build(
    isolation: bool,
    builder: ProjectBuilder,
    outdir: PathType,
    distribution: str,
    config_settings: ConfigSettingsType | None,
    skip_dependency_check: bool,
) -> str:
    if isolation:
        return _build_in_isolated_env(builder, outdir, distribution, config_settings)
    else:
        return _build_in_current_env(builder, outdir, distribution, config_settings, skip_dependency_check)


@contextlib.contextmanager
def _handle_build_error() -> Iterator[None]:
    try:
        yield
    except (BuildException, FailedProcessError) as e:
        _error(str(e))
    except BuildBackendException as e:
        if isinstance(e.exception, subprocess.CalledProcessError):
            _cprint()
            _error(str(e))

        if e.exc_info:
            tb_lines = traceback.format_exception(
                e.exc_info[0],
                e.exc_info[1],
                e.exc_info[2],
                limit=-1,
            )
            tb = ''.join(tb_lines)
        else:
            tb = traceback.format_exc(-1)
        _cprint('\n{dim}{}{reset}\n', tb.strip('\n'))
        _error(str(e))


def _natural_language_list(elements: Sequence[str]) -> str:
    if len(elements) == 0:
        raise IndexError('no elements')
    elif len(elements) == 1:
        return elements[0]
    else:
        return '{} and {}'.format(
            ', '.join(elements[:-1]),
            elements[-1],
        )


def build_package(
    srcdir: PathType,
    outdir: PathType,
    distributions: Sequence[str],
    config_settings: ConfigSettingsType | None = None,
    isolation: bool = True,
    skip_dependency_check: bool = False,
) -> Sequence[str]:
    """
    Run the build process.

    :param srcdir: Source directory
    :param outdir: Output directory
    :param distribution: Distribution to build (sdist or wheel)
    :param config_settings: Configuration settings to be passed to the backend
    :param isolation: Isolate the build in a separate environment
    :param skip_dependency_check: Do not perform the dependency check
    """
    built: list[str] = []
    builder = _ProjectBuilder(srcdir)
    for distribution in distributions:
        out = _build(isolation, builder, outdir, distribution, config_settings, skip_dependency_check)
        built.append(os.path.basename(out))
    return built


def build_package_via_sdist(
    srcdir: PathType,
    outdir: PathType,
    distributions: Sequence[str],
    config_settings: ConfigSettingsType | None = None,
    isolation: bool = True,
    skip_dependency_check: bool = False,
) -> Sequence[str]:
    """
    Build a sdist and then the specified distributions from it.

    :param srcdir: Source directory
    :param outdir: Output directory
    :param distribution: Distribution to build (only wheel)
    :param config_settings: Configuration settings to be passed to the backend
    :param isolation: Isolate the build in a separate environment
    :param skip_dependency_check: Do not perform the dependency check
    """
    if 'sdist' in distributions:
        raise ValueError('Only binary distributions are allowed but sdist was specified')

    builder = _ProjectBuilder(srcdir)
    sdist = _build(isolation, builder, outdir, 'sdist', config_settings, skip_dependency_check)

    sdist_name = os.path.basename(sdist)
    sdist_out = tempfile.mkdtemp(prefix='build-via-sdist-')
    built: list[str] = []
    # extract sdist
    with tarfile.open(sdist) as t:
        t.extractall(sdist_out)
        try:
            builder = _ProjectBuilder(os.path.join(sdist_out, sdist_name[: -len('.tar.gz')]))
            if distributions:
                builder.log(f'Building {_natural_language_list(distributions)} from sdist')
            for distribution in distributions:
                out = _build(isolation, builder, outdir, distribution, config_settings, skip_dependency_check)
                built.append(os.path.basename(out))
        finally:
            shutil.rmtree(sdist_out, ignore_errors=True)
    return [sdist_name] + built


def main_parser() -> argparse.ArgumentParser:
    """
    Construct the main parser.
    """
    parser = argparse.ArgumentParser(
        description=textwrap.indent(
            textwrap.dedent(
                '''
                A simple, correct Python build frontend.

                By default, a source distribution (sdist) is built from {srcdir}
                and a binary distribution (wheel) is built from the sdist.
                This is recommended as it will ensure the sdist can be used
                to build wheels.

                Pass -s/--sdist and/or -w/--wheel to build a specific distribution.
                If you do this, the default behavior will be disabled, and all
                artifacts will be built from {srcdir} (even if you combine
                -w/--wheel with -s/--sdist, the wheel will be built from {srcdir}).
                '''
            ).strip(),
            '    ',
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        'srcdir',
        type=str,
        nargs='?',
        default=os.getcwd(),
        help='source directory (defaults to current directory)',
    )
    parser.add_argument(
        '--version',
        '-V',
        action='version',
        version=f"build {build.__version__} ({','.join(build.__path__)})",
    )
    parser.add_argument(
        '--sdist',
        '-s',
        action='store_true',
        help='build a source distribution (disables the default behavior)',
    )
    parser.add_argument(
        '--wheel',
        '-w',
        action='store_true',
        help='build a wheel (disables the default behavior)',
    )
    parser.add_argument(
        '--outdir',
        '-o',
        type=str,
        help=f'output directory (defaults to {{srcdir}}{os.sep}dist)',
    )
    parser.add_argument(
        '--skip-dependency-check',
        '-x',
        action='store_true',
        help='do not check that build dependencies are installed',
    )
    parser.add_argument(
        '--no-isolation',
        '-n',
        action='store_true',
        help='do not isolate the build in a virtual environment',
    )
    parser.add_argument(
        '--config-setting',
        '-C',
        action='append',
        help='pass options to the backend.  options which begin with a hyphen must be in the form of '
        '"--config-setting=--opt(=value)" or "-C--opt(=value)"',
    )
    return parser


def main(cli_args: Sequence[str], prog: str | None = None) -> None:  # noqa: C901
    """
    Parse the CLI arguments and invoke the build process.

    :param cli_args: CLI arguments
    :param prog: Program name to show in help text
    """
    _setup_cli()
    parser = main_parser()
    if prog:
        parser.prog = prog
    args = parser.parse_args(cli_args)

    distributions = []
    config_settings = {}

    if args.config_setting:
        for arg in args.config_setting:
            setting, _, value = arg.partition('=')
            if setting not in config_settings:
                config_settings[setting] = value
            else:
                if not isinstance(config_settings[setting], list):
                    config_settings[setting] = [config_settings[setting]]

                config_settings[setting].append(value)

    if args.sdist:
        distributions.append('sdist')
    if args.wheel:
        distributions.append('wheel')

    # outdir is relative to srcdir only if omitted.
    outdir = os.path.join(args.srcdir, 'dist') if args.outdir is None else args.outdir

    if distributions:
        build_call = build_package
    else:
        build_call = build_package_via_sdist
        distributions = ['wheel']
    try:
        with _handle_build_error():
            built = build_call(
                args.srcdir, outdir, distributions, config_settings, not args.no_isolation, args.skip_dependency_check
            )
            artifact_list = _natural_language_list(
                ['{underline}{}{reset}{bold}{green}'.format(artifact, **_STYLES) for artifact in built]
            )
            _cprint('{bold}{green}Successfully built {}{reset}', artifact_list)
    except Exception as e:  # pragma: no cover
        tb = traceback.format_exc().strip('\n')
        _cprint('\n{dim}{}{reset}\n', tb)
        _error(str(e))


def entrypoint() -> None:
    main(sys.argv[1:])


if __name__ == '__main__':  # pragma: no cover
    main(sys.argv[1:], 'python -m build')


__all__ = [
    'main',
    'main_parser',
]
