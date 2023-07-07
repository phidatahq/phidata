from __future__ import annotations

from pip._internal.utils.appdirs import user_cache_dir

# The user_cache_dir helper comes straight from pip itself
CACHE_DIR = user_cache_dir("pip-tools")

# The project defaults specific to pip-tools should be written to this filename
CONFIG_FILE_NAME = ".pip-tools.toml"
