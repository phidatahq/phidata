"""
MLX Transcribe Tools will need ffmpeg installed to work.
Install ffmpeg using `brew install ffmpeg` on macOS.
"""

from phi.tools import Toolkit
from phi.utils.log import logger
from typing import Optional

try:
    import mlx_whisper
except ImportError:
    raise ImportError("`mlx_whisper` not installed. Please install using `pip install mlx-whisper`")


class MLXTranscribeTools(Toolkit):
    def __init__(self, file_path: str, path_or_hf_repo: Optional[str] = "mlx-community/whisper-large-v3-turbo"):
        super().__init__(name="transcribe")

        self.file_path = file_path
        self.path_or_hf_repo = path_or_hf_repo

        self.register(self.transcribe)

    def transcribe(self, file_path: str) -> str:
        """
        Transcribe uses Apple's MLX Whisper model.

        Args:
            file_path (str): The path to the audio file to transcribe.
            path_or_hf_repo (str): The path to the local model or the Hugging Face repository to use for the model. Defaults to "mlx-community/whisper-large-v3-turbo".

        Returns:
            str: The transcribed text.
        """
        try:
            logger.info(f"Transcribing audio file {file_path}")
            text = mlx_whisper.transcribe(file_path, path_or_hf_repo=self.path_or_hf_repo)["text"]
            return text
        except Exception as e:
            logger.error(f"Failed to transcribe audio file {e}")
            return f"Error: {e}"
