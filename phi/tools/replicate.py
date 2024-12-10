from os import getenv

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
        model: str = "minimax/video-01",
    ):
        super().__init__(name="replicate_toolkit")
        self.api_key = getenv("REPLICATE_API_TOKEN")
        if not self.api_key:
            logger.error("REPLICATE_API_TOKEN not set. Please set the REPLICATE_API_TOKEN environment variable.")
        self.model = model

        self.register(self.generate_content)

    def generate_content(self, agent: Agent, prompt: str) -> str:
        """
        Use this function to generate an image or a video using a replicate model.
        Args:
            prompt (str): A text description of the content.
        Returns:
            str: Return a URI to the generated video or image.
        """
        output = replicate.run(ref=self.model, input={"prompt": prompt})
        return output
