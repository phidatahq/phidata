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

image_agent_storage_file: str = "tmp/image_agent.db"

image_agent = Agent(
    name="DALL-E Image Agent",
    agent_id="image_agent",
    model=OpenAIChat(id="gpt-4o"),
    tools=[Dalle()],
    description="You are an AI agent that can generate images using DALL-E.",
    instructions=[
        "When the user asks you to create an image, use the `create_image` tool to create the image.",
        "The image will be displayed in the UI automatically below your response, so you don't need to show the image URL in your response.",
        "Politely and courteously let the user know that the image has been generated and will be displayed below as soon as its ready.",
    ],
    markdown=True,
    debug_mode=True,
    add_history_to_messages=True,
    add_datetime_to_instructions=True,
    storage=SqlAgentStorage(table_name="image_agent", db_file="tmp/image_agent.db"),
)

ml_gif_agent = Agent(
    name="ModelsLab GIF Agent",
    agent_id="ml_gif_agent",
    model=OpenAIChat(id="gpt-4o"),
    tools=[ModelsLabs(wait_for_completion=True, file_type=FileType.GIF)],
    description="You are an AI agent that can generate gifs using the ModelsLabs API.",
    instructions=[
        "When the user asks you to create an image, use the `generate_media` tool to create the image.",
        "The image will be displayed in the UI automatically below your response, so you don't need to show the image URL in your response.",
        "Politely and courteously let the user know that the gif has been generated and will be displayed below as soon as its ready.",
    ],
    markdown=True,
    debug_mode=True,
    add_history_to_messages=True,
    add_datetime_to_instructions=True,
    storage=SqlAgentStorage(table_name="ml_gif_agent", db_file="tmp/ml_gif_agent.db"),
)

ml_video_agent = Agent(
    name="ModelsLab Video Agent",
    agent_id="ml_video_agent",
    model=OpenAIChat(id="gpt-4o"),
    tools=[ModelsLabs(wait_for_completion=True, file_type=FileType.MP4)],
    description="You are an AI agent that can generate videos using the ModelsLabs API.",
    instructions=[
        "When the user asks you to create a video, use the `generate_media` tool to create the video.",
        "The video will be displayed in the UI automatically below your response, so you don't need to show the video URL in your response.",
        "Politely and courteously let the user know that the video has been generated and will be displayed below as soon as its ready.",
    ],
    markdown=True,
    debug_mode=True,
    add_history_to_messages=True,
    add_datetime_to_instructions=True,
    storage=SqlAgentStorage(table_name="ml_video_agent", db_file="tmp/ml_video_agent.db"),
)

fal_agent = Agent(
    name="Fal Video Agent",
    agent_id="fal_agent",
    model=OpenAIChat(id="gpt-4o"),
    tools=[FalTools("fal-ai/hunyuan-video")],
    description="You are an AI agent that can generate videos using the Fal API.",
    instructions=[
        "When the user asks you to create a video, use the `generate_media` tool to create the video.",
        "The video will be displayed in the UI automatically below your response, so you don't need to show the video URL in your response.",
        "Politely and courteously let the user know that the video has been generated and will be displayed below as soon as its ready.",
        "Don't send video url in markdown format.",
    ],
    markdown=True,
    debug_mode=True,
    add_history_to_messages=True,
    add_datetime_to_instructions=True,
    storage=SqlAgentStorage(table_name="fal_agent", db_file="tmp/fal_agent.db"),
)



app = Playground(agents=[image_agent, ml_gif_agent, ml_video_agent, fal_agent]).get_app()

if __name__ == "__main__":
    serve_playground_app("multimodal_agent:app", reload=True)
