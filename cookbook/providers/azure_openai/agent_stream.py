from phi.agent import Agent
from phi.model.azure import AzureOpenAIChat
from phi.tools.duckduckgo import DuckDuckGo

agent = Agent(
    model=AzureOpenAIChat(
        model="gpt-4o"
    ),
    tools=[DuckDuckGo()],
    show_tool_calls=True,
    # debug_mode=True,
)
agent.print_response("Whats happening in France?", markdown=True, stream=True)
