"""Run `pip install google-generativeai` to install dependencies."""

from phi.agent import Agent
from phi.model.google import Gemini
from phi.tools import Toolkit


class WeatherTools(Toolkit):
    """
    Simple tool to show function calling with functions that have and don't have parameters.
    """

    def __init__(self):
        super().__init__(name="Weather tool")
        self.register(self.get_weather)
        self.register(self.get_home_weather)

    def get_home_weather(self) -> str:
        """
        Retrieves the weather information for my home.


        Returns:
            str: A JSON-formatted string containing the location and its weather status.
        """
        return "The weather in my home is rainy."

    def get_weather(self, location: str) -> str:
        """
        Retrieves the weather information for a given location.

        Args:
            location (str): The name of the location for which to get the weather.

        Returns:
            str: A JSON-formatted string containing the location and its weather status.
        """
        print(f"Getting weather for {location}")
        return f"""{{"location": {location}, "weather": "sunny"}}"""


agent = Agent(
    model=Gemini(id="gemini-2.0-flash-exp"),
    tools=[WeatherTools()],
    markdown=True,
)
agent.print_response("Can you get the weather in Australia's capital city using the tool?")
