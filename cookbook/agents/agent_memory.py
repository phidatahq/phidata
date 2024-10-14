from rich.pretty import pprint

from phi.agent import Agent, AgentMemory
from phi.tools.yfinance import YFinanceTools

agent = Agent(tools=[YFinanceTools()])

# -*- Print a response
agent.print_response("What is the price of AAPL?", stream=True)

# -*- Get the memory
memory: AgentMemory = agent.memory

# -*- Print Chats
print("============ Chats ============")
pprint(memory.chats)

# -*- Print messages
print("============ Messages ============")
pprint(memory.messages)
