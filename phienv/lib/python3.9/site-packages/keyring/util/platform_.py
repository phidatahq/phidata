import os
import platform
import pathlib


def _settings_root_XP():
    return os.path.join(os.environ['USERPROFILE'], 'Local Settings')


def _settings_root_Vista():
    return os.environ.get('LOCALAPPDATA', os.environ.get('ProgramData', '.'))


def _data_root_Windows():
    release, version, csd, ptype = platform.win32_ver()
    root = _settings_root_XP() if release == 'XP' else _settings_root_Vista()
    return pathlib.Path(root, 'Python Keyring')


def _data_root_Linux():
    """
    Use freedesktop.org Base Dir Specification to determine storage
    location.
    """
    fallback = pathlib.Path.home() / '.local/share'
    root = os.environ.get('XDG_DATA_HOME', None) or fallback
    return pathlib.Path(root, 'python_keyring')


_config_root_Windows = _data_root_Windows


def _check_old_config_root():
    """
    Prior versions of keyring would search for the config
    in XDG_DATA_HOME, but should probably have been
    searching for config in XDG_CONFIG_HOME. If the
    config exists in the former but not in the latter,
    raise a RuntimeError to force the change.
    """
    # disable the check - once is enough and avoids infinite loop
    globals()['_check_old_config_root'] = lambda: None
    config_file_new = os.path.join(_config_root_Linux(), 'keyringrc.cfg')
    config_file_old = os.path.join(_data_root_Linux(), 'keyringrc.cfg')
    if os.path.isfile(config_file_old) and not os.path.isfile(config_file_new):
        msg = (
            "Keyring config exists only in the old location "
            f"{config_file_old} and should be moved to {config_file_new} "
            "to work with this version of keyring."
        )
        raise RuntimeError(msg)


def _config_root_Linux():
    """
    Use freedesktop.org Base Dir Specification to determine config
    location.
    """
    _check_old_config_root()
    fallback = pathlib.Path.home() / '.config'
    key = 'XDG_CONFIG_HOME'
    root = os.environ.get(key, None) or fallback
    return pathlib.Path(root, 'python_keyring')


# by default, use Unix convention
data_root = globals().get('_data_root_' + platform.system(), _data_root_Linux)
config_root = globals().get('_config_root_' + platform.system(), _config_root_Linux)
