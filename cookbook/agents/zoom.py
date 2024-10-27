import os

from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.tools.zoom import ZoomTool


ACCOUNT_ID = os.getenv("ZOOM_ACCOUNT_ID")
CLIENT_ID = os.getenv("ZOOM_CLIENT_ID")
CLIENT_SECRET = os.getenv("ZOOM_CLIENT_SECRET")


class CustomZoomTool(ZoomTool):
    def schedule_meeting(self, topic: str, start_time: str, duration: int) -> str:
        response = super().schedule_meeting(topic, start_time, duration)

        if isinstance(response, str):
            import json

            try:
                meeting_info = json.loads(response)
            except json.JSONDecodeError:
                return "Failed to parse the meeting information."
        else:
            meeting_info = response

        if meeting_info:
            meeting_id = meeting_info.get("id")
            join_url = meeting_info.get("join_url")
            start_time = meeting_info.get("start_time")
            return (
                f"Meeting scheduled successfully!\n\n"
                f"**Meeting ID:** {meeting_id}\n"
                f"**Join URL:** {join_url}\n"
                f"**Start Time:** {start_time}"
            )
        else:
            return "I'm sorry, but I was unable to schedule the meeting."


zoom_tool = CustomZoomTool(account_id=ACCOUNT_ID, client_id=CLIENT_ID, client_secret=CLIENT_SECRET)


agent = Agent(
    name="Zoom Scheduling Agent",
    agent_id="zoom-scheduling-agent",
    model=OpenAIChat(id="gpt-4o"),
    tools=[zoom_tool],
    markdown=True,
    debug_mode=True,
    show_tool_calls=True,
    instructions=[
        "You are an agent designed to schedule Zoom meetings using the Zoom API.",
        "When asked to schedule a meeting, use the `schedule_meeting` function from the `ZoomTool`.",
        "Only pass the necessary parameters to the `schedule_meeting` function unless specifically asked for other parameters.",
        "After scheduling the meeting, provide the meeting details such as Meeting ID, Join URL, and Start Time.",
        "Ensure that all times are in ISO 8601 format (e.g., '2024-12-28T10:00:00Z').",
        "Handle any errors gracefully and inform the user if the meeting could not be scheduled.",
    ],
    system_message=(
        "Do not modify any default parameters of the `schedule_meeting` function unless explicitly "
        "specified in the user's request. Always ensure that the meeting is scheduled successfully "
        "before confirming to the user."
    ),
)

# Use the agent to schedule a meeting based on user input
user_input = "Schedule a meeting titled 'Python Automation Meeting' on 2024-10-31 at 11:00 AM UTC for 60 minutes."
response = agent.run(user_input)
