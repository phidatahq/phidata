from phi.agent import Agent
from phi.tools.linear_tools import LinearTool

agent = Agent(
    name="Linear Tool Agent",
    tools=[LinearTool()],
    show_tool_calls=True,
    markdown=True,
)


user_id = "69069"
issue_id = "6969"

agent.print_response("Get all the details of current user")
agent.print_response(f"Show the issue with the issue id: {issue_id}")
agent.print_response(f"Show all the issues assigned to user id: {user_id}")
agent.print_response("Show all the high priority issues")
