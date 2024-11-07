from pathlib import Path
from typing import Any, Optional

from phi.assistant.openai.file import File
from phi.utils.log import logger


class UrlFile(File):
    url: str
    # Manually provide a filename
    name: Optional[str] = None

    def get_filename(self) -> Optional[str]:
        return self.name or self.url.split("/")[-1] or self.filename

    def read(self) -> Any:
        try:
            import httpx
        except ImportError:
            raise ImportError("`httpx` not installed")

        try:
            from tempfile import TemporaryDirectory

            logger.debug(f"Downloading url: {self.url}")
            with httpx.Client() as client:
                response = client.get(self.url)
                # This will raise an exception for HTTP errors.
                response.raise_for_status()

                # Create a temporary directory
                with TemporaryDirectory() as temp_dir:
                    file_name = self.get_filename()
                    if file_name is None:
                        raise ValueError("Could not determine a file name, please set `name`")

                    file_path = Path(temp_dir).joinpath(file_name)

                    # Write the PDF to a temporary file
                    file_path.write_bytes(response.content)
                    logger.debug(f"PDF downloaded and saved to {file_path.name}")

                    # Read the temporary file
                    return file_path.open("rb")
        except Exception as e:
            logger.error(f"Could not read url: {e}")
