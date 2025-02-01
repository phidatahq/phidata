from agno.agent import Agent
from agno.tools.browserless import BrowserlessTools

agent = Agent(
    tools=[BrowserlessTools()],
    markdown=True,
    show_tool_calls=True,
)
agent.print_response("Scrape the website https://agno.com")
