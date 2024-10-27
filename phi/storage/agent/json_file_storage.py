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
    def serialize(self, data):
        with self.path.open('w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    def deserialize(self):
        with self.path.open('r', encoding='utf-8') as f:
            return json.load(f)
