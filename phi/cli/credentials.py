from typing import Optional, Dict

from phi.cli.settings import phi_cli_settings
from phi.utils.json_io import read_json_file, write_json_file


def save_auth_token(auth_token: str):
    # logger.debug(f"Storing {auth_token} to {str(phi_cli_settings.credentials_path)}")
    _data = {"token": auth_token}
    write_json_file(phi_cli_settings.credentials_path, _data)


def read_auth_token() -> Optional[str]:
    # logger.debug(f"Reading token from {str(phi_cli_settings.credentials_path)}")
    _data: Dict = read_json_file(phi_cli_settings.credentials_path)  # type: ignore
    if _data is None:
        return None

    try:
        return _data.get("token")
    except Exception:
        pass
    return None
