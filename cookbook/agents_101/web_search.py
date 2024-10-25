"""Run `pip install openai duckduckgo-search` to install dependencies."""

from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.tools.duckduckgo import DuckDuckGo

def create_web_agent():
    return Agent(
        name="Web Agent",
        model=OpenAIChat(id="gpt-4o"),
        tools=[DuckDuckGo()],
        show_tool_calls=True,
        markdown=True,
    )

if __name__ == "__main__":
    web_agent = create_web_agent()
    web_agent.print_response("Whats happening in France?", stream=True)
