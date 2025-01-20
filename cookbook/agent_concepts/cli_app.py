from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.yfinance import YFinanceTools

agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    tools=[
        DuckDuckGoTools(),
        YFinanceTools(
            stock_price=True,
            analyst_recommendations=True,
            company_info=True,
            company_news=True,
        ),
    ],
    # show tool calls in the response
    show_tool_calls=True,
    # add a tool to read chat history
    read_chat_history=True,
    # return response in markdown
    markdown=True,
    # enable debug mode
    # debug_mode=True,
)

agent.cli_app(stream=True)
