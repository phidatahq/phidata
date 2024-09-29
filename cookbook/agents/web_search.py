from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.tools.duckduckgo import DuckDuckGo

web_search_agent = Agent(model=OpenAIChat(id="gpt-4o"), tools=[DuckDuckGo()], show_tool_calls=True, markdown=True)
web_search_agent.print_response("Share 3 news stories from France")
