"""
pip install fal-client
"""

from os import getenv
from typing import Optional

from phi.agent import Agent
from phi.tools import Toolkit
from phi.utils.log import logger

try:
    import fal_client  # type: ignore
except ImportError:
    raise ImportError("`fal_client` not installed. Please install using `pip install fal-client`")


class HunyuanVideo(Toolkit):
    def __init__(
        self,
        api_key: Optional[str] = None,
    ):
        super().__init__(name="hunyuan_video")

        self.api_key = api_key or getenv("FAL_API_KEY")
        if not self.api_key:
            logger.error("FAL_API_KEY not set. Please set the FAL_API_KEY environment variable.")

        self.register(self.generate_video)

    def on_queue_update(self, update):
        if isinstance(update, fal_client.InProgress) and update.logs:
            for log in update.logs:
                logger.info(log["message"])

    def generate_video(self, agent: Agent, prompt: str) -> str:
        """
        Use this function to generate a video given a prompt.

        Args:
            prompt (str): A text description of the desired video.

        Returns:
            str: Generated video URL.
        """
        try:
            result = fal_client.subscribe(
                "fal-ai/hunyuan-video",
                arguments={"prompt": prompt},
                with_logs=True,
                on_queue_update=self.on_queue_update,
            )
            video_url = result.get("video", {}).get("url", "")
            return video_url
        except Exception as e:
            logger.error(f"Failed to generate video: {e}")
            return f"Error: {e}"
