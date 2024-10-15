from phi.agent import Agent
from phi.tools.resend_tools import ResendTools

from_email = "<enter_from_email>"
to_email = "<enter_to_email>"

agent = Agent(tools=[ResendTools(from_email=from_email)], show_tool_calls=True)
agent.print_response(f"Send an email to {to_email} greeting them with hello world")
