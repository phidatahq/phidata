import json
from os import getenv
from typing import Optional

try:
    import requests
except ImportError:
    raise ImportError("`requests` not installed. Please install using `pip install requests`")

from phi.tools import Toolkit
from phi.utils.log import logger


class ModelsLabs(Toolkit):
    def __init__(
        self,
        api_key: Optional[str] = None,
        url: str = "https://modelslab.com/api/v6/video/text2video",
    ):
        super().__init__(name="models_labs")

        self.url = url

        self.api_key = api_key or getenv("MODELS_LAB_API_KEY")
        if not self.api_key:
            logger.error("MODELS_LAB_API_KEY not set. Please set the MODELS_LAB_API_KEY environment variable.")

        self.register(self.generate_video)

    def generate_video(self, prompt: str) -> str:
        """Use this function to generate a video given a prompt.

        Args:
            prompt (str): A text description of the desired video.

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

            logger.info(f"Generating video for prompt: {prompt}")
            response = requests.request("POST", self.url, data=payload, headers=headers)
            logger.info(f"Response - {response.text}")
            response.raise_for_status()

            result = response.json()
            if "error" in result:
                logger.error(f"Failed to generate video: {result['error']}")
                return f"Error: {result['error']}"

            parsed_result = json.dumps(result, indent=4)
            logger.info(f"Video generated successfully: {parsed_result}")
            return parsed_result
        except Exception as e:
            logger.error(f"Failed to generate video: {e}")
            return f"Error: {e}"
