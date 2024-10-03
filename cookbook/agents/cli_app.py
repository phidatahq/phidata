from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.tools.duckduckgo import DuckDuckGo

agent = Agent(model=OpenAIChat(id="gpt-4o"), tools=[DuckDuckGo()], show_tool_calls=True, read_chat_history=True)
agent.cli_app(markdown=True)
