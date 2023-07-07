"""
Creates and manages isolated build environments.
"""

from __future__ import annotations

import abc
import functools
import logging
import os
import platform
import shutil
import subprocess
import sys
import sysconfig
import tempfile
import warnings

from collections.abc import Callable, Collection
from types import TracebackType

import build


try:
    import virtualenv
except ModuleNotFoundError:
    virtualenv = None


_logger = logging.getLogger(__name__)


class IsolatedEnv(metaclass=abc.ABCMeta):
    """Abstract base of isolated build environments, as required by the build project."""

    @property
    @abc.abstractmethod
    def executable(self) -> str:
        """The executable of the isolated build environment."""
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def scripts_dir(self) -> str:
        """The scripts directory of the isolated build environment."""
        raise NotImplementedError

    @abc.abstractmethod
    def install(self, requirements: Collection[str]) -> None:
        """
        Install packages from PEP 508 requirements in the isolated build environment.

        :param requirements: PEP 508 requirements
        """
        raise NotImplementedError


@functools.lru_cache(maxsize=None)
def _should_use_virtualenv() -> bool:
    import packaging.requirements

    # virtualenv might be incompatible if it was installed separately
    # from build. This verifies that virtualenv and all of its
    # dependencies are installed as specified by build.
    return virtualenv is not None and not any(
        packaging.requirements.Requirement(d[1]).name == 'virtualenv'
        for d in build.check_dependency('build[virtualenv]')
        if len(d) > 1
    )


def _subprocess(cmd: list[str]) -> None:
    """Invoke subprocess and output stdout and stderr if it fails."""
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        print(e.output.decode(), end='', file=sys.stderr)
        raise e


class IsolatedEnvBuilder:
    """Builder object for isolated environments."""

    def __init__(self) -> None:
        self._path: str | None = None

    def __enter__(self) -> IsolatedEnv:
        """
        Create an isolated build environment.

        :return: The isolated build environment
        """
        # Call ``realpath`` to prevent spurious warning from being emitted
        # that the venv location has changed on Windows. The username is
        # DOS-encoded in the output of tempfile - the location is the same
        # but the representation of it is different, which confuses venv.
        # Ref: https://bugs.python.org/issue46171
        self._path = os.path.realpath(tempfile.mkdtemp(prefix='build-env-'))
        try:
            # use virtualenv when available (as it's faster than venv)
            if _should_use_virtualenv():
                self.log('Creating virtualenv isolated environment...')
                executable, scripts_dir = _create_isolated_env_virtualenv(self._path)
            else:
                self.log('Creating venv isolated environment...')
                executable, scripts_dir = _create_isolated_env_venv(self._path)
            return _IsolatedEnvVenvPip(
                path=self._path,
                python_executable=executable,
                scripts_dir=scripts_dir,
                log=self.log,
            )
        except Exception:  # cleanup folder if creation fails
            self.__exit__(*sys.exc_info())
            raise

    def __exit__(
        self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: TracebackType | None
    ) -> None:
        """
        Delete the created isolated build environment.

        :param exc_type: The type of exception raised (if any)
        :param exc_val: The value of exception raised (if any)
        :param exc_tb: The traceback of exception raised (if any)
        """
        if self._path is not None and os.path.exists(self._path):  # in case the user already deleted skip remove
            shutil.rmtree(self._path)

    @staticmethod
    def log(message: str) -> None:
        """
        Prints message

        The default implementation uses the logging module but this function can be
        overwritten by users to have a different implementation.

        :param msg: Message to output
        """
        if sys.version_info >= (3, 8):
            _logger.log(logging.INFO, message, stacklevel=2)
        else:
            _logger.log(logging.INFO, message)


class _IsolatedEnvVenvPip(IsolatedEnv):
    """
    Isolated build environment context manager

    Non-standard paths injected directly to sys.path will still be passed to the environment.
    """

    def __init__(
        self,
        path: str,
        python_executable: str,
        scripts_dir: str,
        log: Callable[[str], None],
    ) -> None:
        """
        :param path: The path where the environment exists
        :param python_executable: The python executable within the environment
        :param log: Log function
        """
        self._path = path
        self._python_executable = python_executable
        self._scripts_dir = scripts_dir
        self._log = log

    @property
    def path(self) -> str:
        """The location of the isolated build environment."""
        return self._path

    @property
    def executable(self) -> str:
        """The python executable of the isolated build environment."""
        return self._python_executable

    @property
    def scripts_dir(self) -> str:
        return self._scripts_dir

    def install(self, requirements: Collection[str]) -> None:
        """
        Install packages from PEP 508 requirements in the isolated build environment.

        :param requirements: PEP 508 requirement specification to install

        :note: Passing non-PEP 508 strings will result in undefined behavior, you *should not* rely on it. It is
               merely an implementation detail, it may change any time without warning.
        """
        if not requirements:
            return

        self._log('Installing packages in isolated environment... ({})'.format(', '.join(sorted(requirements))))

        # pip does not honour environment markers in command line arguments
        # but it does for requirements from a file
        with tempfile.NamedTemporaryFile('w+', prefix='build-reqs-', suffix='.txt', delete=False) as req_file:
            req_file.write(os.linesep.join(requirements))
        try:
            cmd = [
                self.executable,
                '-Im',
                'pip',
                'install',
                '--use-pep517',
                '--no-warn-script-location',
                '-r',
                os.path.abspath(req_file.name),
            ]
            _subprocess(cmd)
        finally:
            os.unlink(req_file.name)


def _create_isolated_env_virtualenv(path: str) -> tuple[str, str]:
    """
    We optionally can use the virtualenv package to provision a virtual environment.

    :param path: The path where to create the isolated build environment
    :return: The Python executable and script folder
    """
    cmd = [str(path), '--no-setuptools', '--no-wheel', '--activators', '']
    result = virtualenv.cli_run(cmd, setup_logging=False)
    executable = str(result.creator.exe)
    script_dir = str(result.creator.script_dir)
    return executable, script_dir


@functools.lru_cache(maxsize=None)
def _fs_supports_symlink() -> bool:
    """Return True if symlinks are supported"""
    # Using definition used by venv.main()
    if not sys.platform.startswith('win'):
        return True

    # Windows may support symlinks (setting in Windows 10)
    with tempfile.NamedTemporaryFile(prefix='build-symlink-') as tmp_file:
        dest = f'{tmp_file}-b'
        try:
            os.symlink(tmp_file.name, dest)
            os.unlink(dest)
            return True
        except (OSError, NotImplementedError, AttributeError):
            return False


def _create_isolated_env_venv(path: str) -> tuple[str, str]:
    """
    On Python 3 we use the venv package from the standard library.

    :param path: The path where to create the isolated build environment
    :return: The Python executable and script folder
    """
    import venv

    import packaging.version

    if sys.version_info < (3, 8):
        import importlib_metadata as metadata
    else:
        from importlib import metadata

    symlinks = _fs_supports_symlink()
    try:
        with warnings.catch_warnings():
            if sys.version_info[:3] == (3, 11, 0):
                warnings.filterwarnings('ignore', 'check_home argument is deprecated and ignored.', DeprecationWarning)
            venv.EnvBuilder(with_pip=True, symlinks=symlinks).create(path)
    except subprocess.CalledProcessError as exc:
        raise build.FailedProcessError(exc, 'Failed to create venv. Maybe try installing virtualenv.') from None

    executable, script_dir, purelib = _find_executable_and_scripts(path)

    # Get the version of pip in the environment
    pip_distribution = next(iter(metadata.distributions(name='pip', path=[purelib])))  # type: ignore[no-untyped-call]
    current_pip_version = packaging.version.Version(pip_distribution.version)

    if platform.system() == 'Darwin' and int(platform.mac_ver()[0].split('.')[0]) >= 11:
        # macOS 11+ name scheme change requires 20.3. Intel macOS 11.0 can be told to report 10.16 for backwards
        # compatibility; but that also fixes earlier versions of pip so this is only needed for 11+.
        is_apple_silicon_python = platform.machine() != 'x86_64'
        minimum_pip_version = '21.0.1' if is_apple_silicon_python else '20.3.0'
    else:
        # PEP-517 and manylinux1 was first implemented in 19.1
        minimum_pip_version = '19.1.0'

    if current_pip_version < packaging.version.Version(minimum_pip_version):
        _subprocess([executable, '-m', 'pip', 'install', f'pip>={minimum_pip_version}'])

    # Avoid the setuptools from ensurepip to break the isolation
    _subprocess([executable, '-m', 'pip', 'uninstall', 'setuptools', '-y'])
    return executable, script_dir


def _find_executable_and_scripts(path: str) -> tuple[str, str, str]:
    """
    Detect the Python executable and script folder of a virtual environment.

    :param path: The location of the virtual environment
    :return: The Python executable, script folder, and purelib folder
    """
    config_vars = sysconfig.get_config_vars().copy()  # globally cached, copy before altering it
    config_vars['base'] = path
    scheme_names = sysconfig.get_scheme_names()
    if 'venv' in scheme_names:
        # Python distributors with custom default installation scheme can set a
        # scheme that can't be used to expand the paths in a venv.
        # This can happen if build itself is not installed in a venv.
        # The distributors are encouraged to set a "venv" scheme to be used for this.
        # See https://bugs.python.org/issue45413
        # and https://github.com/pypa/virtualenv/issues/2208
        paths = sysconfig.get_paths(scheme='venv', vars=config_vars)
    elif 'posix_local' in scheme_names:
        # The Python that ships on Debian/Ubuntu varies the default scheme to
        # install to /usr/local
        # But it does not (yet) set the "venv" scheme.
        # If we're the Debian "posix_local" scheme is available, but "venv"
        # is not, we use "posix_prefix" instead which is venv-compatible there.
        paths = sysconfig.get_paths(scheme='posix_prefix', vars=config_vars)
    elif 'osx_framework_library' in scheme_names:
        # The Python that ships with the macOS developer tools varies the
        # default scheme depending on whether the ``sys.prefix`` is part of a framework.
        # But it does not (yet) set the "venv" scheme.
        # If the Apple-custom "osx_framework_library" scheme is available but "venv"
        # is not, we use "posix_prefix" instead which is venv-compatible there.
        paths = sysconfig.get_paths(scheme='posix_prefix', vars=config_vars)
    else:
        paths = sysconfig.get_paths(vars=config_vars)
    executable = os.path.join(paths['scripts'], 'python.exe' if sys.platform.startswith('win') else 'python')
    if not os.path.exists(executable):
        raise RuntimeError(f'Virtual environment creation failed, executable {executable} missing')

    return executable, paths['scripts'], paths['purelib']


__all__ = [
    'IsolatedEnvBuilder',
    'IsolatedEnv',
]
