import json
from pathlib import Path
from typing import Union
from .generic_file_storage import GenericFileStorage

class JsonFileStorage(GenericFileStorage):
    def __init__(self, path: Union[str, Path]):
        super().__init__(path)

    @property
    def fileExtension(self) -> str:
        return ".json"
    def serialize(self, data: dict) -> str:
        return json.dumps(data, ensure_ascii=False, indent=4)

    def deserialize(self, data: str) -> dict:
        return json.loads(data)
