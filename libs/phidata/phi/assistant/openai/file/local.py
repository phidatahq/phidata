from pathlib import Path
from typing import Any, Union, Optional

from phi.assistant.openai.file import File
from phi.utils.log import logger


class LocalFile(File):
    path: Union[str, Path]

    @property
    def filepath(self) -> Path:
        if isinstance(self.path, str):
            return Path(self.path)
        return self.path

    def get_filename(self) -> Optional[str]:
        return self.filepath.name or self.filename

    def read(self) -> Any:
        logger.debug(f"Reading file: {self.filepath}")
        return self.filepath.open("rb")
