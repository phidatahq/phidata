import os
from os import getenv
from urllib.parse import urlparse
from uuid import uuid4

from phi.agent import Agent
from phi.model.content import Video, Image
from phi.tools import Toolkit
from phi.utils.log import logger

try:
    import replicate
    from replicate.helpers import FileOutput
except ImportError:
    raise ImportError("`replicate` not installed. Please install using `pip install replicate`.")


class ReplicateTools(Toolkit):
    def __init__(
        self,
        model: str = "minimax/video-01",
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

        # Parse the URL to extract the file extension
        parsed_url = urlparse(output.url)
        path = parsed_url.path
        _, ext = os.path.splitext(path)
        ext = ext.lower()

        # Define supported extensions
        image_extensions = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp"}
        video_extensions = {".mp4", ".mov", ".avi", ".mkv", ".flv", ".wmv", ".webm"}

        media_id = str(uuid4())

        if ext in image_extensions:
            agent.add_image(
                Image(
                    id=media_id,
                    url=output.url,
                )
            )
            media_type = "image"
        elif ext in video_extensions:
            agent.add_video(
                Video(
                    id=media_id,
                    url=output.url,
                )
            )
            media_type = "video"
        else:
            logger.error(f"Unsupported media type with extension '{ext}' for URL: {output.url}")
            return f"Unsupported media type with extension '{ext}'."

        return f"{media_type.capitalize()} generated successfully at {output.url}"
