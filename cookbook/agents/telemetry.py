
from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.tools.yfinance import YFinanceTools
from phi.storage.agent.postgres import PgAgentStorage

agent = Agent(
    model=OpenAIChat(model="gpt-4o"),
    tools=[YFinanceTools(stock_price=True)],
    show_tool_calls=True,
    markdown=True,
    # debug_mode=True,
    storage=PgAgentStorage(table_name="agent_sessions", db_url="postgresql+psycopg://ai:ai@localhost:5532/ai"),
)

# run: RunResponse = agent.run("What is the stock price of NVDA")
# print(run.content)
# print("------------*******************------------")
# print(run)
# print("------------*******************------------")
# print("------------*******************------------")
# for m in run.messages:
#     print("---")
#     print(m)
#     print("---")

# run_stream: Iterator[RunResponse] = agent.run("What is the stock price of NVDA", stream=True)
# for run in run_stream:
#     print(run.content)

# agent.create_session()
agent.print_response("What is the stock price of NVDA")
