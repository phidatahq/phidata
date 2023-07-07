"""The `version` module holds the version information for Pydantic."""
from typing import Tuple

__all__ = 'VERSION', 'version_info'

VERSION = '2.0.2'
"""The version of Pydantic."""


def version_info() -> str:
    """Return complete version information for Pydantic and its dependencies."""
    import platform
    import sys
    from importlib import import_module
    from pathlib import Path

    import pydantic_core._pydantic_core as pdc

    optional_deps = []
    for p in 'devtools', 'email-validator', 'typing-extensions':
        try:
            import_module(p.replace('-', '_'))
        except ImportError:  # pragma: no cover
            continue
        optional_deps.append(p)

    info = {
        'pydantic version': VERSION,
        'pydantic-core version': f'{pdc.__version__} {pdc.build_profile} build profile',
        'install path': Path(__file__).resolve().parent,
        'python version': sys.version,
        'platform': platform.platform(),
        'optional deps. installed': optional_deps,
    }
    return '\n'.join('{:>30} {}'.format(k + ':', str(v).replace('\n', ' ')) for k, v in info.items())


def parse_mypy_version(version: str) -> Tuple[int, ...]:
    """Parse mypy string version to tuple of ints.

    This function is included here rather than the mypy plugin file because the mypy plugin file cannot be imported
    outside a mypy run.

    It parses normal version like `0.930` and dev version
    like `0.940+dev.04cac4b5d911c4f9529e6ce86a27b44f28846f5d.dirty`.

    Args:
        version: The mypy version string.

    Returns:
        A tuple of ints. e.g. (0, 930).
    """
    return tuple(map(int, version.partition('+')[0].split('.')))
