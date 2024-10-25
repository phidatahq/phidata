"""Run `pip install atlassian-python-api` to install dependencies."""
from phi.agent import Agent
from phi.tools.confluence_tools import ConfluenceTools

agent = Agent(tools=[ConfluenceTools()], show_tool_calls=True)

agent.print_response("Get the page with the title 'Hello World' in the space 'DEV'")
agent.print_response("Create a page with the title 'Hello World' in the space 'DEV' and the content 'Hello, World!'")
agent.print_response("Get the page with the id '12345'")
