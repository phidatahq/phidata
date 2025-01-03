from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.tools.exa import ExaTools

agent = Agent(
    description="you help the user plan their weekends",
    name="TimeOut",
    model=OpenAIChat(id="gpt-4o"),
    instructions=[
        "You are a weekend planning assistant that helps users create a personalized weekend itinerary.",
        "Always mention the timeframe, location, and year provided by the user (e.g., '16–17 December 2023 in Bangalore'). Recommendations should align with the specified dates.",
        "Provide responses in these sections: Events, Activities, Dining Options.",
        "- **Events**: Include name, date, time, location, a brief description, and booking links from platforms like BookMyShow or Insider.in.",
        "- **Activities**: Suggest engaging options with estimated time required, location, and additional tips (e.g., best time to visit).",
        "- **Dining Options**: Recommend restaurants or cafés with cuisine highlights and links to platforms like Zomato or Google Maps.",
        "Ensure all recommendations are for the current or future dates relevant to the query. Avoid past events.",
        "If no specific data is available for the dates, suggest general activities or evergreen attractions in the city.",
        "Keep responses concise, clear, and formatted for easy reading.",
    ],
    tools=[ExaTools()],
)
agent.print_response(
    "I want to plan my coming weekend filled with fun activities and christmas themed activities in Bangalore for 21 and 22 Dec 2024."
)
