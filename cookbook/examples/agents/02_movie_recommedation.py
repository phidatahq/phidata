from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.tools.firecrawl import FirecrawlTools
from phi.tools.exa import ExaTools

movie_recommedation_agent = Agent(
    name="PopcornPal",
    tools=[
        ExaTools(),
        FirecrawlTools(scrape=True, crawl=False), 
    ],
    model=OpenAIChat(id="gpt-4o"),
    description="You are a movie recommendation agent. You search movies by doing Exa search then scraping through a website.",
    instructions=[
        "Scrape the website https://www.themoviedb.org/ or https://www.imdb.com/",
        "Give a result with rating of the movie, it's genre, description, recommended age to watch,language, similar trailers like of recommended one and upcoming movies, best movies to watch for that particular year, remember to give the output in this format",
        "Do not give the link to the movie",
        "Use tables to give the result"
        "You should give the upcoming trailers, that are expected to come after the ones you have recommended"
    ],
    show_tool_calls=True,
    debug_mode=True,      
    markdown=True,
)
movie_recommedation_agent.print_response("Suggest four latest indian romantic movie released in 2024", stream=True)