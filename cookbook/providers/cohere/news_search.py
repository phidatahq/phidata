from phi.agent import Agent
from phi.model.cohere import CohereChat
from phi.tools.duckduckgo import DuckDuckGo

agent = Agent(
    model=CohereChat(id="command-r-plus"),
    tools=[DuckDuckGo()],
    show_tool_calls=True,
    markdown=True,
)

agent.print_response("Provide the latest news on NVIDIA", stream=False)
