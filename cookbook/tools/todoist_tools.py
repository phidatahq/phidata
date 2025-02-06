"""
Example showing how to use the Todoist Tools with Agno

Requirements:
- Todoist API Token (get from https://app.todoist.com/app/settings/integrations/developer)
- pip install todoist-api-python

Usage:
- Set the following environment variables:
    export TODOIST_API_TOKEN="your_api_token"

- Or provide them when creating the TodoistTools instance
"""

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.todoist import TodoistTools


todoist_agent = Agent(
    name="Todoist Agent",
    role="Manage your todoist tasks",
    instructions=[
        "You can create, read, update and delete tasks in todoist.",
        "You can also get the list of projects and tasks in todoist.",
    ],
    agent_id="todoist-agent",
    model=OpenAIChat(id="gpt-4o"),
    tools=[TodoistTools()],
    markdown=True,
    debug_mode=True,
    show_tool_calls=True,
)


todoist_agent.print_response("Create a todoist task to buy groceries tomorrow at 10am")
