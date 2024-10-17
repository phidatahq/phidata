from phi.tools import Toolkit
from typing import Optional
from os import getenv
from phi.utils.log import logger


try:
    from openai import OpenAI
except ImportError:
    raise ImportError("`openai` not installed. Please install using `pip install openai`")


class DalleTools(Toolkit):
    def __init__(
        self,
        model: str = "dall-e-3",
        size: str = "1280x720",
        quality: str = "standard",
        n: int = 1,
        api_key: Optional[str] = None,
    ):
        super().__init__(name="dalle")

        self.model = model
        self.size = size
        self.quality = quality
        self.n = n

        self.api_key = api_key or getenv("OPENAI_API_KEY")
        if not self.api_key:
            logger.error("OPENAI_API_KEY not set. Please set the OPENAI_API_KEY environment variable.")

        self.register(self.generate_image)

    def generate_image(self, prompt: str) -> str:
        """Use this function to generate an image using DALL-E.

        Args:
            prompt (str): The prompt to generate an image from.

        Returns:
            str: The URL of the generated image, or an error message.
        """
        if not self.api_key:
            return "Please set the OPENAI_API_KEY"

        try:
            client = OpenAI(api_key=self.api_key)
            logger.info(f"Generating image for prompt: {prompt}")
            response = client.images.generate(
                model=self.model,
                prompt=prompt,
                size=self.size,
                quality=self.quality,
                n=self.n,
            )
            return response.data[0].url
        except Exception as e:
            logger.error(f"Failed to generate image: {e}")
            return f"Error: {e}"
