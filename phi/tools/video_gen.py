from os import getenv
from typing import Optional

from phi.tools import Toolkit
from phi.utils.log import logger

import requests
import json


class VideoGenTools(Toolkit):
    def __init__(
        self,
        api_key: Optional[str] = None,
        url: str = "https://modelslab.com/api/v6/video/text2video",
    ):
        super().__init__(name="video_gen")

        self.api_key = api_key or getenv("MODELS_LAB_API_KEY")
        if not self.api_key:
            logger.error("MODELS_LAB_API_KEY not set. Please set the MODELS_LAB_API_KEY environment variable.")

        self.url = url

        self.register(self.generate_video)

    def generate_video(self, prompt: str) -> str:
        """Use this function to generate a video using VideoGen.

        Args:
            prompt (str): The input text for video generation.

        Returns:
            str: The generated video information in JSON format.
        """
        if not self.api_key:
            return "Please set the MODELS_LAB_API_KEY"

        try:
            payload = json.dumps(
                {
                    "key": self.api_key,
                    "prompt": prompt,
                    "height": 512,
                    "width": 512,
                    "num_frames": 25,
                    "webhook": None,
                    "output_type": "gif",
                    "track_id": None,
                    "negative_prompt": "low quality",
                    "model_id": "zeroscope",
                    "instant_response": False,
                }
            )

            headers = {"Content-Type": "application/json"}

            logger.info("Generating video with prompt: %s", prompt)
            response = requests.request("POST", self.url, data=payload, headers=headers)
            logger.info("response - %s", response.text)
            response.raise_for_status()

            result = response.json()
            parsed_result = json.dumps(result, indent=4)
            logger.info("Video generation request successful")
            return parsed_result
        except requests.RequestException as e:
            logger.error("Failed to generate video: %s", e)
            return "Error: %s" % e
        except json.JSONDecodeError as e:
            logger.error("Failed to parse response: %s", e)
