from rich.pretty import pprint

from phi.agent import Agent, AgentMemory
from phi.tools.yfinance import YFinanceTools

agent = Agent(tools=[YFinanceTools()])

# -*- Print a response
agent.print_response("What is the price of AAPL?", stream=True)

# -*- Get the memory
memory: AgentMemory = agent.memory

# -*- Print Chat History
print("============ Chat History ============")
pprint(memory.chat_history)

# -*- Print Run Messages
print("============ Run Messages ============")
pprint(memory.run_messages)
