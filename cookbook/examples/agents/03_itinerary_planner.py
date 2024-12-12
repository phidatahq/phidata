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
        "Use Exa to search and extract relevant data from reputable travel platforms.",
        "Collect information on flights, accommodations, local attractions, and estimated costs from these sources.",
        "Ensure that the gathered data is accurate and tailored to the user's preferences, such as destination, group size, and budget constraints.",
        "Create a clear and concise itinerary that includes: detailed day-by-day travel plan, suggested transportation and accommodation options, activity recommendations (e.g., sightseeing, dining, events), an estimated cost breakdown (covering transportation, accommodation, food, and activities).",
        "If a particular website or travel option is unavailable, provide alternatives from other trusted sources.",
        "Do not include direct links to external websites or booking platforms in the response.",
    ],
)

itinerary_agent.print_response(
    "I want to plan an offsite for 14 people for 3 days (28th-30th March) in London within 10k dollars. Please suggest options for places to stay, activities, and co working spaces and a detailed itinerary for the 3 days with transportation and activities",
    stream=True,
)
