"""Run `pip install openai slack-sdk` to install dependencies."""

import os

from phi.agent import Agent
from phi.tools.webex import WebexTools

webex_token = os.getenv("WEBEX_TEAMS_ACCESS_TOKEN")
webex_tool = WebexTools(token=webex_token)

agent = Agent(tools=[webex_tool], show_tool_calls=True)

#Send a message to a Space in Webex
agent.print_response("Send a message 'Hello from Phi!' to the webex Welcome space", markdown=True)

#List all space in Webex
agent.print_response("List all space on our Webex", markdown=True)