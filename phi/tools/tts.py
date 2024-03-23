import json
from typing import List, Optional

from phi.document import Document
from phi.knowledge.website import WebsiteKnowledgeBase
from phi.tools import ToolRegistry
from phi.utils.log import logger


class TTSTools(ToolRegistry):
    def __init__(self):
        super().__init__(name="TTS_tools")
        self.register(self.save_audio)
        self.register(self.read_audio)

    def save_audio(self, text: str) -> str:
        """
        """
        from openai import OpenAI
        client = OpenAI()
        from playsound import playsound

        speech_file_path = "speech.mp3"
        response = client.audio.speech.create(
        model="tts-1",
        voice="alloy",
        input=text,
        )

        response.stream_to_file(speech_file_path)

        playsound(speech_file_path)

        # with openai.audio.speech.with_streaming_response.create(
        # model="tts-1",
        # voice="alloy",
        # input=text,
        # ) as response:
        #     response.stream_to_file(speech_file_path)
        #     playsound(speech_file_path)

        return speech_file_path

    def read_audio(self, speech_file_path: str) -> str:
        """
        """
        from playsound import playsound
        playsound(speech_file_path)

        return "Audio played"

