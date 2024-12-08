from phi.agent import Agent
from phi.tools.googlecalender import GoogleCalenderTools
from phi.model.mistral import MistralChat
import datetime
import os

try:
    from tzlocal import get_localzone_name
except ImportError:
    raise ImportError("`tzlocal not found` install using `pip install tzlocal`")

GOOGLE_CALENDER_INSTRUCTION = f"""
You are scheduing assistant . Today is {datetime.datetime.now()} and Users timezone is {get_localzone_name()}.
You should help users to perform these actions in their google calender :
    - get their scheduled events from a certain date and time
    - create events based on provided details
"""

agent = Agent(
    tools=[GoogleCalenderTools(credentials_path="<PATH_TO_YOUR_CREDENTIALS_FILE>")],
    show_tool_calls=True,
    instructions=[GOOGLE_CALENDER_INSTRUCTION],
    provider=MistralChat(api_key=os.getenv("MISTRAL_API_KEY")),
    add_datetime_to_instructions=True,
)

agent.print_response("Give me the list of todays events", markdown=True)

# agent.print_response(
#     "create an event today from 5pm to 6pm, make the title as test event v1 and description as this is a test event", markdown=True)
