from phi.agent import Agent
from phi.tools.jira_tools import JiraTools

# Initialize JiraTools with your Jira server URL and credentials
jira_tools = JiraTools(
    server_url="https://your-jira-instance.atlassian.net", username="your-email@example.com", token=""
)

# Create the agent and pass the JiraTools instance
agent = Agent(tools=[jira_tools], debug_mode=True, show_tool_calls=True)

# Example usage: Get details of a specific issue
agent.print_response("Get the details of issue PROJ-38", markdown=True)

# Example usage: Create a new issue
agent.print_response(
    "Create a new issue in project PROJ with summary 'New Feature Request' and description 'Add support for XYZ feature.'",
    markdown=True,
)

# Example usage: Search for issues
agent.print_response("Find all issues in project PROJ", markdown=True)

# Example usage: Add a comment to an issue
agent.print_response("Add a comment to issue PROJ-38 saying 'This issue needs to be prioritized.'", markdown=True)
