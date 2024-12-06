"""Run `pip install openai sqlalchemy 'fastapi[standard]' phidata` to install dependencies."""

from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.tools.dalle import Dalle
from phi.playground import Playground, serve_playground_app
from phi.storage.agent.sqlite import SqlAgentStorage


image_agent_storage_file: str = "tmp/image_agent.db"

image_agent = Agent(
    name="Image Agent",
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

app = Playground(agents=[image_agent]).get_app()

if __name__ == "__main__":
    serve_playground_app("image_agent:app", reload=True)
