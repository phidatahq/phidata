from phi.agent import Agent
from phi.model.cohere import CohereChat
from phi.tools.duckduckgo import DuckDuckGo

agent = Agent(
    model=CohereChat(model="command-r-plus"),
    tools=[DuckDuckGo()],
    show_tool_calls=True,
    # debug_mode=True,
)
agent.print_response("Whats happening in France?", markdown=True, stream=True)
