from phi.agent import Agent
from phi.tools.phi import PhiTools

# Create an Agent with the Phi tool
agent = Agent(tools=[PhiTools()], name="Phi Workspace Manager")

# Example 1: Create a new agent app
agent.print_response("Create a new agent-app called agent-app-turing", markdown=True)

# Example 3: Start a workspace
agent.print_response("Start the workspace agent-app-turing", markdown=True)
