from os import getenv
from typing import Optional, Literal, List

from phi.agent import Agent
from phi.tools import Toolkit
from phi.utils.log import logger

try:
    from openai import OpenAI
    from openai.types.image import Image
    from openai.types.images_response import ImagesResponse
except ImportError:
    raise ImportError("`openai` not installed. Please install using `pip install openai`")


class Dalle(Toolkit):
    def __init__(
        self,
        model: str = "dall-e-3",
        n: int = 1,
        size: Optional[Literal["256x256", "512x512", "1024x1024", "1792x1024", "1024x1792"]] = "1024x1024",
        quality: Literal["standard", "hd"] = "standard",
        style: Literal["vivid", "natural"] = "vivid",
        api_key: Optional[str] = None,
    ):
        super().__init__(name="dalle")

        self.model = model
        self.n = n
        self.size = size
        self.quality = quality
        self.style = style
        self.api_key = api_key or getenv("OPENAI_API_KEY")

        # Validations
        if model not in ["dall-e-3", "dall-e-2"]:
            raise ValueError("Invalid model. Please choose from 'dall-e-3' or 'dall-e-2'.")
        if size not in ["256x256", "512x512", "1024x1024", "1792x1024", "1024x1792"]:
            raise ValueError(
                "Invalid size. Please choose from '256x256', '512x512', '1024x1024', '1792x1024', '1024x1792'."
            )
        if quality not in ["standard", "hd"]:
            raise ValueError("Invalid quality. Please choose from 'standard' or 'hd'.")
        if not isinstance(n, int) or n <= 0:
            raise ValueError("Invalid number of images. Please provide a positive integer.")
        if model == "dall-e-3" and n > 1:
            raise ValueError("Dall-e-3 only supports a single image generation.")

        if not self.api_key:
            logger.error("OPENAI_API_KEY not set. Please set the OPENAI_API_KEY environment variable.")

        self.register(self.generate_image)
        # TODO:
        # - Add support for response_format
        # - Add support for saving images
        # - Add support for editing images

    def generate_image(self, agent: Agent, prompt: str) -> str:
        """Use this function to generate an image for a prompt.

        Args:
            prompt (str): A text description of the desired image.

        Returns:
            str: The URL of the generated image, or an error message.
        """
        if not self.api_key:
            return "Please set the OPENAI_API_KEY"

        try:
            client = OpenAI(api_key=self.api_key)
            logger.info(f"Generating image for prompt: {prompt}")
            response: ImagesResponse = client.images.generate(
                prompt=prompt,
                model=self.model,
                n=self.n,
                quality=self.quality,
                size=self.size,
                style=self.style,
            )

            # TODO: add validations
            data: List[Image] = response.data
            logger.info(f"Images Generated: {len(data)}")

            # Update the run response with the image URLs
            agent.run_response.images = response.model_dump()
            return response.model_dump_json()
        except Exception as e:
            logger.error(f"Failed to generate image: {e}")
            return f"Error: {e}"
