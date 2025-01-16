from agno.agent import Agent
from agno.media import ImageInput
from agno.models.openai import OpenAIChat
from agno.tools.duckduckgo import DuckDuckGoTools

agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    tools=[DuckDuckGoTools()],
    markdown=True,
    # Set add_history_to_messages=true to add the previous chat history to the messages sent to the Model.
    add_history_to_messages=True,
    # Number of historical responses to add to the messages.
    num_history_responses=3,
)

agent.print_response(
    "Tell me about this image and give me the latest news about it.",
    images=[
        ImageInput(url="https://upload.wikimedia.org/wikipedia/commons/b/bf/Krakow_-_Kosciol_Mariacki.jpg")
    ],
)

agent.print_response("Tell me where I can get more images?")
