from phi.agent import Agent
from phi.tools.zendesk import ZendeskTools

agent = Agent(tools=[ZendeskTools()], show_tool_calls=True)
agent.print_response("How do I login?", markdown=True)
