import yaml
from pathlib import Path
from typing import Union
from .generic_file_storage import GenericFileStorage

class YamlFileStorage(GenericFileStorage):
    def __init__(self, path: Union[str, Path]):
        super().__init__(path)

    @property
    def fileExtension(self) -> str:
        return ".yaml"

    def serialize(self, data: dict) -> str:
        return yaml.dump(data, default_flow_style=False)

    def deserialize(self, data: str) -> dict:
        return yaml.safe_load(data)
