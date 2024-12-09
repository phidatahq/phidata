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


class Fal(Toolkit):
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "fal-ai/hunyuan-video",
    ):
        super().__init__(name="fal")

        self.api_key = api_key or getenv("FAL_API_KEY")
        if not self.api_key:
            logger.error("FAL_API_KEY not set. Please set the FAL_API_KEY environment variable.")

        self.register(self.run)

    def on_queue_update(self, update):
        if isinstance(update, fal_client.InProgress) and update.logs:
            for log in update.logs:
                logger.info(log["message"])

    def run(self, agent: Agent, prompt: str, model: str) -> str:
        """
        Use this function to run a model with a given prompt.

        Args:
            prompt (str): A text description of the task.
            model (str): The model to use.
        Returns:
            str: Return the result of the model.
        """
        try:
            result = fal_client.subscribe(
                model,
                arguments={"prompt": prompt},
                with_logs=True,
                on_queue_update=self.on_queue_update,
            )
            if video_url := result.get("video", {}).get("url", ""):
                return video_url
            elif image_url := result.get("image", {}).get("url", ""):
                print(image_url)
                return image_url
            else:
                return str(result)
        except Exception as e:
            logger.error(f"Failed to run model: {e}")
            return f"Error: {e}"
