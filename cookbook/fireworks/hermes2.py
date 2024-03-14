import json
import httpx

from phi.assistant import Assistant
from phi.llm.fireworks import Fireworks


def get_the_weather(city: str, state: str):
    """Get the weather for a city and state"""

    return f"hot and sunny in {city}, {state}"


assistant = Assistant(
    llm=Fireworks(model="accounts/fireworks/models/hermes-2-pro-mistral-7b"),
    tools=[get_the_weather],
    show_tool_calls=True,
    debug_mode=True,
)
assistant.print_response("Whats the weather in london?")
