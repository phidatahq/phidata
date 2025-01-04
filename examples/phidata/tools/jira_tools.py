from phi.agent import Agent
from phi.tools.jira_tools import JiraTools

agent = Agent(tools=[JiraTools()])
agent.print_response("Find all issues in project PROJ", markdown=True)
