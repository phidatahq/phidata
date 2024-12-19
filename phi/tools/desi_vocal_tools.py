from phi.tools import Toolkit
from os import getenv
from typing import Optional
from phi.utils.log import logger
from phi.agent import Agent
from phi.model.content import Audio
from uuid import uuid4

import requests


class DesiVocalTools(Toolkit):
    def __init__(
        self,
        api_key: Optional[str] = None,
        voice_id: Optional[str] = "f27d74e5-ea71-4697-be3e-f04bbd80c1a8",
    ):
        super().__init__(name="desi_vocal_tools")

        self.api_key = api_key or getenv("DESI_VOCAL_API_KEY")
        if not self.api_key:
            logger.error("DESI_VOCAL_API_KEY not set. Please set the DESI_VOCAL_API_KEY environment variable.")

        self.voice_id = voice_id

        self.register(self.get_voices)
        self.register(self.text_to_speech)

    # def get_voices(self) -> str:
    #     try:
    #         url = "https://prod-api2.desivocal.com/dv/api/v0/tts_api/voices"
    #         response = requests.get(url)
    #         for voice in response.json():
                
    #         return str(response.text)
    #     except Exception as e:
    #         logger.error(f"Failed to get voices: {e}")
    #         return f"Error: {e}"

    def text_to_speech(self, agent: Agent, text: str) -> str:
        try:
            url = "https://prod-api2.desivocal.com/dv/api/v0/tts_api/generate"

            payload = {
                "text": text,
                "voice_id": self.voice_id,
            }

            headers = {
                "X_API_KEY": self.api_key,
                "Content-Type": "application/json",
            }

            response = requests.post(url, headers=headers, json=payload)

            audio_url = response.json()["s3_path"]

            agent.add_audio(Audio(id=str(uuid4()), url=audio_url))

            return audio_url
        except Exception as e:
            logger.error(f"Failed to generate audio: {e}")
            return f"Error: {e}"
