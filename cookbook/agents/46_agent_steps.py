from rich.pretty import pprint
from phi.agent import Agent
from phi.agent.step.reason import Reason
from phi.agent.step.task import Task
from phi.agent.step.respond import Respond
from phi.model.openai import OpenAIChat
from phi.tools.yfinance import YFinanceTools

agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    tools=[YFinanceTools(stock_price=True, analyst_recommendations=True, stock_fundamentals=True)],
    instructions=["Use tables to display data"],
    steps=[
        Task(instructions="Pull stock prices"),
        Task(instructions="Pull analyst recommendations"),
        Task(instructions="Pull stock fundamentals"),
        Respond(instructions="Answer the original question"),
    ],
    # reasoning=True,
    markdown=True,
    debug_mode=True,
    show_tool_calls=True,
)

agent.print_response("Write a report comparing NVDA to TSLA", stream=True, show_full_reasoning=True)
pprint(agent.run_response.messages)
pprint(agent.memory.get_messages())
