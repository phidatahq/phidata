from rich.pretty import pprint
from phi.agent import Agent, RunResponse
from phi.model.openai import OpenAIChat
from phi.tools.yfinance import YFinanceTools
from phi.storage.agent.postgres import PgAgentStorage

agent = Agent(
    model=OpenAIChat(model="gpt-4o"),
    tools=[YFinanceTools(stock_price=True)],
    show_tool_calls=True,
    markdown=True,
    # debug_mode=True,
    # monitoring=False,
    storage=PgAgentStorage(table_name="agent_sessions", db_url="postgresql+psycopg://ai:ai@localhost:5532/ai"),
)

run1: RunResponse = agent.run("What is the stock price of NVDA")
# run2: RunResponse = agent.run({"text": "What is the stock price of NVDA", "image": "https://example.com/image.jpg"})
pprint(run1)
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
# agent.print_response("What is the stock price of NVDA?")
