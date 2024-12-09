import json
from os import getenv
from typing import Optional

from phi.agent import Agent
from phi.tools import Toolkit
from phi.utils.log import logger

try:
    import replicate
except ImportError:
    raise ImportError("`replicate` not installed. Please install using `pip install replicate`.")


class ReplicateToolKit(Toolkit):
    def __init__(
        self,
        model: str = "tencent/hunyuan-video",
    ):
        super().__init__(name="replicate_toolkit")
        self.api_key = getenv("REPLICATE_API_TOKEN")
        if not self.api_key:
            logger.error("REPLICATE_API_TOKEN not set. Please set the REPLICATE_API_TOKEN environment variable.")
        self.model = model

        self.register(self.generate_video)

    def generate_video(self, agent: Agent, prompt: str) -> str:
        """
        Use this function to generate a video.
        Args:
            prompt (str): A text description of the task.
        Returns:
            str: Return a URI to the generated video.
        """
        output = replicate.run(
            ref=self.model,
            input={
                "prompt": prompt
            }
        )
        return output

