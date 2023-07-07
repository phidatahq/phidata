import json
from datetime import datetime, date
from pathlib import Path
from typing import Optional, Dict, Any

from phi.utils.log import logger


class CustomJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime) or isinstance(o, date):
            return o.isoformat()

        return json.JSONEncoder.default(self, o)


def read_json_file(file_path: Optional[Path]) -> Optional[Dict[str, Any]]:
    if file_path is not None and file_path.exists() and file_path.is_file():
        logger.debug(f"Reading {file_path}")
        return json.loads(file_path.read_text())
    return None


def write_json_file(file_path: Optional[Path], data: Optional[Dict[str, Any]]) -> None:
    if file_path is not None and data is not None:
        logger.debug(f"Writing {file_path}")
        file_path.write_text(json.dumps(data, cls=CustomJSONEncoder, indent=4))
