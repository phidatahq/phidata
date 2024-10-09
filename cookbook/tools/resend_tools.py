from phi.agent import Agent
from phi.tools.resend_tools import ResendTools

agent = Agent(tools=[ResendTools(from_email="<enter_from_email>")], debug_mode=True)

agent.print_response("send email to <enter_to_email> greeting them with hello world")
