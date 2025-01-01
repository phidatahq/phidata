"""
pip install fal-client
"""

from os import getenv
from typing import Optional

from phi.agent import Agent
from phi.tools import Toolkit
from phi.utils.log import logger
from phi.model.content import Video, Image
from uuid import uuid4


try:
    import fal_client  # type: ignore
except ImportError:
    raise ImportError("`fal_client` not installed. Please install using `pip install fal-client`")


class FalTools(Toolkit):
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "fal-ai/hunyuan-video",
    ):
        super().__init__(name="fal")

        self.api_key = api_key or getenv("FAL_KEY")
        if not self.api_key:
            logger.error("FAL_KEY not set. Please set the FAL_KEY environment variable.")
        self.model = model
        self.seen_logs: set[str] = set()
        self.register(self.generate_media)

    def on_queue_update(self, update):
        if isinstance(update, fal_client.InProgress) and update.logs:
            for log in update.logs:
                message = log["message"]
                if message not in self.seen_logs:
                    logger.info(message)
                    self.seen_logs.add(message)

    def generate_media(self, agent: Agent, prompt: str) -> str:
        """
        Use this function to run a model with a given prompt.

        Args:
            prompt (str): A text description of the task.
        Returns:
            str: Return the result of the model.
        """
        try:
            result = fal_client.subscribe(
                self.model,
                arguments={"prompt": prompt},
                with_logs=True,
                on_queue_update=self.on_queue_update,
            )

            media_id = str(uuid4())

            if "image" in result:
                url = result.get("image", {}).get("url", "")
                agent.add_image(
                    Image(
                        id=media_id,
                        url=url,
                    )
                )
                media_type = "image"
            elif "video" in result:
                url = result.get("video", {}).get("url", "")
                agent.add_video(
                    Video(
                        id=media_id,
                        url=url,
                    )
                )
                media_type = "video"
            else:
                logger.error(f"Unsupported type in result: {result}")
                return f"Unsupported type in result: {result}"

            return f"{media_type.capitalize()} generated successfully at {url}"
        except Exception as e:
            logger.error(f"Failed to run model: {e}")
            return f"Error: {e}"
