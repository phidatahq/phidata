import os
from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.tools.youtube_tools import YouTubeTools
from phi.tools.apify import ApifyTools
from phi.tools.exa import ExaTools

ai_recipe_agent = Agent(
    tools=[
        ExaTools(),
        ApifyTools(web_scraper=True),
        YouTubeTools()
    ],
    model=OpenAIChat(id="gpt-4o"),
    description="You are a recipe suggestor. Suggest recipes based on input ingredients by doing Google Search and summarizing YouTube videos.",
    instructions=[
        "Search exa for recipes",
        "Then scrape the website https://www.allrecipes.com/ for therecipe",
        "Then search Youtube with description and give a summary",
    ],
    show_tool_calls=True,
    debug_mode=True,      
    markdown=True,         
    stream=True         
)

ai_recipe_agent.print_response(
    "I have milk and butter, suggest me with some recipe."
)
