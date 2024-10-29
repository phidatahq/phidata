"""
MLX Transcribe Tools will need ffmpeg installed to work.
Install ffmpeg using `brew install ffmpeg` on macOS.

MLX Transcribe Tools will need the `mlx-whisper` library installed to work.
Install `mlx-whisper` using `pip install mlx-whisper`
"""

from phi.tools.mlx_transcribe import MLXTranscribeTools
from phi.agent import Agent
from phi.model.openai import OpenAIChat
import os

file_path = os.path.expanduser("~/path/to/file.mp3")


agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    tools=[MLXTranscribeTools(file_path=file_path)],
    name="Transcribe Agent",
    markdown=True,
)

agent.print_response(f"Transcribing file {file_path}", markdown=True)
