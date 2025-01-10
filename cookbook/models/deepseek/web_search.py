"""Run `pip install duckduckgo-search` to install dependencies."""

from agno.agent import Agent
from agno.models.deepseek import DeepSeekChat
from agno.tools.duckduckgo import DuckDuckGo

agent = Agent(
    model=DeepSeekChat(id="deepseek-chat"),
    tools=[DuckDuckGo()],
    show_tool_calls=True,
    markdown=True,
)

agent.print_response("Whats happening in France?", stream=True)