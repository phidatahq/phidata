import time
import json
from os import getenv
from typing import Optional, Dict, Any

from phi.agent import Agent
from phi.tools import Toolkit
from phi.utils.log import logger

try:
    from lumaai import LumaAI
except ImportError:
    raise ImportError("`lumaai` not installed. Please install using `pip install lumaai`")


class LumaLab(Toolkit):
    def __init__(
        self,
        api_key: Optional[str] = None,
        wait_for_completion: bool = True,
        poll_interval: int = 3,
        max_wait_time: int = 300,  # 5 minutes
    ):
        super().__init__(name="luma_lab")

        self.wait_for_completion = wait_for_completion
        self.poll_interval = poll_interval
        self.max_wait_time = max_wait_time
        self.api_key = api_key or getenv("LUMAAI_API_KEY")

        if not self.api_key:
            logger.error("LUMAAI_API_KEY not set. Please set the LUMAAI_API_KEY environment variable.")

        self.client = LumaAI(auth_token=self.api_key)
        self.register(self.generate_video)

    def generate_video(
        self,
        agent: Agent,
        prompt: str,
        loop: bool = False,
        aspect_ratio: str = "16:9",
        keyframes: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Use this function to generate a video given a prompt.

        Args:
            prompt (str): A text description of the desired video.
            loop (bool, optional): Whether the video should loop. Defaults to False.
            aspect_ratio (str, optional): Aspect ratio of the video. Defaults to "16:9".
            keyframes (Dict[str, Any], optional): Keyframe configuration for image-to-video or video extension.

        Returns:
            str: A message indicating if the video has been generated successfully or an error message.
        """
        if not self.api_key:
            return "Please set the LUMAAI_API_KEY"

        try:
            # Create generation request
            generation_params = {
                "prompt": prompt,
                "loop": loop,
                "aspect_ratio": aspect_ratio,
            }
            if keyframes:
                generation_params["keyframes"] = keyframes

            logger.debug(f"Generating video with params: {generation_params}")
            generation = self.client.generations.create(**generation_params)

            if not self.wait_for_completion:
                agent.add_video(json.dumps({"id": generation.id}))
                return f"Video generation started with ID: {generation.id}"

            # Poll for completion
            completed = False
            seconds_waited = 0
            while not completed and seconds_waited < self.max_wait_time:
                generation = self.client.generations.get(id=generation.id)

                if generation.state == "completed":
                    completed = True
                    video_url = generation.assets.video
                    agent.add_video(json.dumps({
                        "id": generation.id,
                        "url": video_url,
                        "state": "completed"
                    }))
                    return f"Video generated successfully: {video_url}"
                elif generation.state == "failed":
                    return f"Generation failed: {generation.failure_reason}"

                logger.info(f"Generation in progress... State: {generation.state}")
                time.sleep(self.poll_interval)
                seconds_waited += self.poll_interval

            if not completed:
                return f"Video generation timed out after {self.max_wait_time} seconds"

        except Exception as e:
            logger.error(f"Failed to generate video: {e}")
            return f"Error: {e}"
