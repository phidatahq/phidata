import os 
from phi.agent import Agent
from phi.model.openai import OpenAIChat
from clickup_tool import ClickUpTools

clickup_agent = Agent(
    name="ClickUp Agent",
    role="Manage ClickUp tasks and spaces",
    model=OpenAIChat(model="gpt-4o-mini"),
    tools=[ClickUpTools(list_spaces=True, list_lists=True, list_tasks=True)],
    instructions=[
        "You are a ClickUp assistant that helps users manage their tasks and spaces.",
            "You can:",
            "1. List all available spaces",
            "2. List tasks from a specific space",
            "3. List all lists in a space",
            "4. Create new tasks with title, description, and status",
            
            "When creating tasks:",
            "- Always get space name, task name, and description",
            "- Status can be: todo, in progress, or done",
            "- If status is not specified, use 'todo' as default",
            
            "Be helpful and guide users if they need more information.",
        ],
    show_tool_calls=True,
    markdown=True
    )

clickup_agent.print_response("List all spaces i have", markdown=True,)
