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
)


todoist_agent.print_response("Create a todoist task to buy groceries tomorrow at 10am")
