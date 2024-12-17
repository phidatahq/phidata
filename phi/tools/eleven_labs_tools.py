"""
pip install elevenlabs
"""

from typing import Optional, Literal
from os import getenv, makedirs, path
from phi.tools import Toolkit
from phi.utils.log import logger
from phi.agent import Agent
from uuid import uuid4

try:
    from elevenlabs import ElevenLabs  # type: ignore
except ImportError:
    raise ImportError("`elevenlabs` not installed. Please install using `pip install elevenlabs`")

OutputFormat = Literal[
    "mp3_22050_32",    # mp3 with 22.05kHz sample rate at 32kbps
    "mp3_44100_32",    # mp3 with 44.1kHz sample rate at 32kbps
    "mp3_44100_64",    # mp3 with 44.1kHz sample rate at 64kbps
    "mp3_44100_96",    # mp3 with 44.1kHz sample rate at 96kbps
    "mp3_44100_128",   # default, mp3 with 44.1kHz sample rate at 128kbps
    "mp3_44100_192",   # mp3 with 44.1kHz sample rate at 192kbps (Creator tier+)
    "pcm_16000",       # PCM format (S16LE) with 16kHz sample rate
    "pcm_22050",       # PCM format (S16LE) with 22.05kHz sample rate
    "pcm_24000",       # PCM format (S16LE) with 24kHz sample rate
    "pcm_44100",       # PCM format (S16LE) with 44.1kHz sample rate (Pro tier+)
    "ulaw_8000"        # μ-law format with 8kHz sample rate (for Twilio)
]


class ElevenLabsTools(Toolkit):
    def __init__(
        self,
        api_key: Optional[str] = None,
        target_directory: str = "audio_generations",
        voice_id: str = "21m00Tcm4TlvDq8ikWAM",
        model_id: str = "eleven_multilingual_v2",
        output_format: OutputFormat = "mp3_44100_64",
    ):
        super().__init__(name="elevenlabs")

        self.api_key = api_key or getenv("ELEVEN_LABS_API_KEY")
        if not self.api_key:
            logger.error("ELEVEN_LABS_API_KEY not set. Please set the ELEVEN_LABS_API_KEY environment variable.")

        self.target_directory = target_directory
        self.voice_id = voice_id
        self.model_id = model_id
        self.output_format = output_format

        if not path.exists(self.target_directory):
            makedirs(self.target_directory, exist_ok=True)

        self.client = ElevenLabs(api_key=self.api_key)
        self.register(self.generate_audio)

    def generate_audio(self, agent: Agent, prompt: str) -> str:
        """
        Use this function to generate audio from a text prompt. The audio is stored to a file in the target_directory.

        Args:
            prompt (str): Text to generate audio from.
        Returns:
            str: Return the path to the generated audio file.
        """
        try:
            audio_generator = self.client.text_to_speech.convert(
                voice_id=self.voice_id,
                model_id=self.model_id,
                text=prompt,
                output_format=self.output_format,
            )

            # Determine file extension based on output format
            if self.output_format.startswith("mp3"):
                extension = "mp3"
            elif self.output_format.startswith("pcm"):
                extension = "wav"
            elif self.output_format.startswith("ulaw"):
                extension = "ulaw"
            else:
                extension = "mp3" 

            output_filename = f"{uuid4()}.{extension}"
            output_path = path.join(self.target_directory, output_filename)

            with open(output_path, "wb") as f:
                for chunk in audio_generator:
                    f.write(chunk)

            return output_path

        except Exception as e:
            logger.error(f"Failed to generate audio: {e}")
            return f"Error: {e}"
