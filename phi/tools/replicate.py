import json
from os import getenv
from uuid import uuid4

from phi.agent import Agent
from phi.model.content import Video
from phi.tools import Toolkit
from phi.utils.log import logger

try:
    import replicate
    from replicate.helpers import FileOutput
except ImportError:
    raise ImportError("`replicate` not installed. Please install using `pip install replicate`.")


class ReplicateToolKit(Toolkit):
    def __init__(
        self,
        model: str = "minimax/video-01",
        wait_for_completion: bool = True,
        max_wait_time: int = 300,  # 5 minutes
    ):
        super().__init__(name="replicate_toolkit")
        self.api_key = getenv("REPLICATE_API_TOKEN")
        if not self.api_key:
            logger.error("REPLICATE_API_TOKEN not set. Please set the REPLICATE_API_TOKEN environment variable.")
        self.model = model

        self.register(self.generate_media)

    def generate_media(self, agent: Agent, prompt: str) -> str:
        """
        Use this function to generate an image or a video using a replicate model.
        Args:
            prompt (str): A text description of the content.
        Returns:
            str: Return a URI to the generated video or image.
        """
        output: FileOutput = replicate.run(ref=self.model, input={"prompt": prompt})

        # Update the run response with the video URLs
        agent.add_video(Video(
            id=str(uuid4()),
            url=output.url,
        ))

        return f"Media generated successfully at {output.url}"
