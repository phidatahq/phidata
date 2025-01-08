"""Run `pip install yfinance` to install dependencies."""

from agno.agent import Agent, RunResponse  # noqa
from agno.models.deepseek import DeepSeekChat
from agno.tools.yfinance import YFinanceTools

agent = Agent(
    model=DeepSeekChat(id="deepseek-chat"),
    tools=[
        YFinanceTools(
            company_info=True,
            stock_fundamentals=True,
        )
    ],
    show_tool_calls=True,
    debug_mode=True,
    markdown=True,
)

# Get the response in a variable
# run: RunResponse = agent.run("What is the stock price of NVDA and TSLA")
# print(run.content)

# Print the response on the terminal
agent.print_response("Give me in-depth analysis of NVDA and TSLA")
