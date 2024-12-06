from phi.model.openai import OpenAIChat
from phi.agent import Agent
from phi.tools.exa import ExaTools

itinerary_agent = Agent(
    name="GlobeHopper",
    model=OpenAIChat(id="gpt-4o"),
    tools=[ExaTools()],
    markdown=True,
    description="You are an expert itinerary planning agent. Your role is to assist users in creating detailed, customized travel plans tailored to their preferences and needs.",
    instructions=[
        "Use Exa to search and extract relevant data from popular travel websites.",
        "Gather information on flights, accommodations, local attractions, and approximate costs from these platforms.",
        "Ensure that the collected data is accurate and aligns with the user's preferences and requirements, such as the destination, group size, and budget constraints.",
        "Structure a clear, concise itinerary that includes recommendations for transportation, stay, and activities without providing exact reservation numbers or bookings.",
        "If a specific website or travel option is unavailable, suggest alternatives from other reliable sources."
    ],
)

itinerary_agent.print_response("I want to plan an offsite for 14 people in a place like London. Please suggest options for places to stay, activities, and other recommendations", stream=True)
