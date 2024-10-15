from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.tools.duckduckgo import DuckDuckGo
from phi.tools.yfinance import YFinanceTools

web_agent = Agent(
    name="Web Agent",
    role="Search the web for information",
    model=OpenAIChat(id="gpt-4o"),
    tools=[DuckDuckGo()],
    markdown=True,
    show_tool_calls=True,
)

finance_agent = Agent(
    name="Finance Agent",
    role="Get financial data",
    model=OpenAIChat(id="gpt-4o"),
    tools=[YFinanceTools(stock_price=True, analyst_recommendations=True, company_info=True, company_news=True)],
    instructions=["Always use tables to display data"],
    markdown=True,
    show_tool_calls=True,
)

agent_team = Agent(
    team=[web_agent, finance_agent],
    show_tool_calls=True,
    markdown=True,
)

agent_team.print_response("Reaserch the web for NVDA and share analyst recommendations", stream=True)
