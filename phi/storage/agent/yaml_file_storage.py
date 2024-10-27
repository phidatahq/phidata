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

    def serialize(self, data: dict, path: Path) -> None:
        with path.open('w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False)

    def deserialize(self, path: Path) -> dict:
        with path.open('r', encoding='utf-8') as f:
            return yaml.safe_load(f)
