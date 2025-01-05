from phi.agent import Agent
from phi.tools.sleep import Sleep

# Create an Agent with the Sleep tool
agent = Agent(tools=[Sleep()], name="Sleep Agent")

# Example 1: Sleep for 2 seconds
agent.print_response("Sleep for 2 seconds")

# Example 2: Sleep for a longer duration
agent.print_response("Sleep for 5 seconds")
