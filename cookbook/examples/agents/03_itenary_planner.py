from phi.model.openai import OpenAIChat
from phi.agent import Agent
from phi.tools.exa import ExaTools
from phi.tools.apify import ApifyTools

agent = Agent(
    name="GlobeHopper",
    model=OpenAIChat(id="gpt-4o"),
    tools=[ExaTools(), ApifyTools(web_scraper=True)],
    show_tool_calls=True,
    markdown=True,
    debug_mode=True,
    description="You are an itinerary planner agent. Your role is to assist users in creating detailed and personalized travel plans.",
    instructions=[
        "Crawl the website for itenary planning https://www.tripadvisor.in/Trips or https://www.makemytrip.com/",
        "Make a concise itenary with flight options, residence options, tourist places, and the estimated budget",
        "Look for user inputs and priortise it if they have specific demands",
        "Do not give any numbers for reservations"
    ],
)

agent.print_response("I want to go to Bombay,with four members please make an itenary")

