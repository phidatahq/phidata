from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.tools.apify import ApifyTools
from phi.tools.exa import ExaTools

movie_recommedation_agent = Agent(
    name="PopcornPal",
    tools=[
        ExaTools(),
        ApifyTools() 
    ],
    model=OpenAIChat(id="gpt-4o"),
    description="You are a movie recommendation agent. You search movies by doing Exa search then scraping through a website.",
    instructions=[
        "Crawl the website https://www.imdb.com/",
        "Give a result with rating of the movie, it's genre, description, recommended age to watch,language, similar trailers like of recommended one and upcoming movies, best movies to watch for that particular year, remember to give the output in this format",
        "Do not give the IMDB link to the movie",
        "Use tables to give the result"
    ],
    show_tool_calls=True,
    debug_mode=False,      
    markdown=True,         
    stream=True 
)
movie_recommedation_agent.print_response("Suggest some indian romantic movie")