from phi.agent import Agent
from phi.model.openai import OpenAIChat

agent = Agent(
    model=OpenAIChat(model="gpt-4o"),
    show_tool_calls=True,
    markdown=True,
    debug_mode=True,
)

agent.print_response("Share a healthy breakfast recipe", stream=True)
