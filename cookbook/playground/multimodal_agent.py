"""
1. Install dependencies: `pip install openai sqlalchemy 'fastapi[standard]' phidata requests`
2. Authenticate with phidata: `phi auth`
3. Run the agent: `python cookbook/playground/multimodal_agent.py`

Docs on Agent UI: https://docs.phidata.com/agent-ui
"""

from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.tools.dalle import Dalle
from phi.tools.models_labs import ModelsLabs
from phi.model.response import FileType
from phi.playground import Playground, serve_playground_app
from phi.storage.agent.sqlite import SqlAgentStorage
from phi.tools.fal_tools import FalTools
from pydantic import BaseModel, Field

image_agent_storage_file: str = "tmp/image_agent.db"

image_agent = Agent(
    name="DALL-E Image Agent",
    agent_id="image_agent",
    model=OpenAIChat(id="gpt-4o"),
    tools=[Dalle()],
    description="You are an AI agent that can generate images using DALL-E.",
    instructions=[
        "When the user asks you to create an image, use the `create_image` tool to create the image.",
        "Don't provide the URL of the image in the response. Only describe what image was generated."
    ],
    markdown=True,
    debug_mode=True,
    add_history_to_messages=True,
    add_datetime_to_instructions=True,
    storage=SqlAgentStorage(table_name="image_agent", db_file=image_agent_storage_file),
)

ml_gif_agent = Agent(
    name="ModelsLab GIF Agent",
    agent_id="ml_gif_agent",
    model=OpenAIChat(id="gpt-4o"),
    tools=[ModelsLabs(wait_for_completion=True, file_type=FileType.GIF)],
    description="You are an AI agent that can generate gifs using the ModelsLabs API.",
    instructions=[
        "When the user asks you to create an image, use the `generate_media` tool to create the image.",
        "Don't provide the URL of the image in the response. Only describe what image was generated."
    ],
    markdown=True,
    debug_mode=True,
    add_history_to_messages=True,
    add_datetime_to_instructions=True,
    storage=SqlAgentStorage(table_name="ml_gif_agent", db_file=image_agent_storage_file),
)

ml_video_agent = Agent(
    name="ModelsLab Video Agent",
    agent_id="ml_video_agent",
    model=OpenAIChat(id="gpt-4o"),
    tools=[ModelsLabs(wait_for_completion=True, file_type=FileType.MP4)],
    description="You are an AI agent that can generate videos using the ModelsLabs API.",
    instructions=[
        "When the user asks you to create a video, use the `generate_media` tool to create the video.",
        "Don't provide the URL of the video in the response. Only describe what video was generated."
    ],
    markdown=True,
    debug_mode=True,
    add_history_to_messages=True,
    add_datetime_to_instructions=True,
    storage=SqlAgentStorage(table_name="ml_video_agent", db_file=image_agent_storage_file),
)

fal_agent = Agent(
    name="Fal Video Agent",
    agent_id="fal_agent",
    model=OpenAIChat(id="gpt-4o"),
    tools=[FalTools("fal-ai/hunyuan-video")],
    description="You are an AI agent that can generate videos using the Fal API.",
    instructions=[
        "When the user asks you to create a video, use the `generate_media` tool to create the video.",
        "Don't provide the URL of the video in the response. Only describe what video was generated."
    ],
    markdown=True,
    debug_mode=True,
    add_history_to_messages=True,
    add_datetime_to_instructions=True,
    storage=SqlAgentStorage(table_name="fal_agent", db_file=image_agent_storage_file),
)


app = Playground(agents=[image_agent, ml_gif_agent, ml_video_agent, fal_agent]).get_app(use_async=False)

if __name__ == "__main__":
    serve_playground_app("multimodal_agent:app", reload=True)
