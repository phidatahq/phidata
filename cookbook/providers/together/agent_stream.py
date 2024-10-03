from typing import Iterator  # noqa
from phi.agent import Agent, RunResponse  # noqa
from phi.model.together import Together
from phi.tools.yfinance import YFinanceTools

agent = Agent(
    model=Together(id="mistralai/Mixtral-8x7B-Instruct-v0.1"),
    tools=[YFinanceTools(stock_price=True)],
    show_tool_calls=True,
    markdown=True,
)

# Get the response in a variable
# run_response: Iterator[RunResponse] = agent.run("What is the stock price of NVDA and TSLA", stream=True)
# for chunk in run_response:
#     print(chunk.content)

# Print the response on the terminal
agent.print_response("What is the stock price of NVDA and TSLA", stream=True)
