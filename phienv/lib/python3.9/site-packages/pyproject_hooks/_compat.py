__all__ = ("tomllib",)

import sys

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib
