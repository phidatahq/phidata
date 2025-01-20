"""
Business Contact Search Agent for finding and extracting business contact information.
"""
from dotenv import load_dotenv
load_dotenv()

from phi.agent import Agent
from phi.tools.crawl4ai_tools import Crawl4aiTools
from phi.tools.google_map_tools import GoogleMapTools

agent = Agent(
    name="Business contact info agent",
    tools=[
        GoogleMapTools(),  # For searching businesses on Google Maps
        Crawl4aiTools(max_length=5000),  # For scraping business websites
    ],
    description="You are a business contact information researcher specializing in finding accurate contact details for businesses.",
    instructions=[
        "When given a search query to find business contact information:",
        "Use the Google Maps Search tool to find relevant businesses in the specified location.",
        "For each business found by Google Maps Search tool, if they have a website, use web crawler tool to extract other business information.",
        "Whatever information you dont get from google maps, try to get it from website.",
    ],
    markdown=True,
    show_tool_calls=True,
    debug_mode=True,
)

agent.print_response(
    "get me the business details of indian restaurants in phoenix AZ",
    markdown=True,
    stream=True
)