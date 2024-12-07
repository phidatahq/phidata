from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.tools.firecrawl import FirecrawlTools

movie_recommendation_agent = Agent(
    name="PopcornPal",
    tools=[
        FirecrawlTools(scrape=True, crawl=False), 
    ],
    model=OpenAIChat(id="gpt-4o"),
    description=(
        "You are PopcornPal, a movie recommendation agent that searches and scrapes movie websites to provide detailed recommendations, "
        "including ratings, genres, descriptions, trailers, and upcoming releases."
    ),
    instructions=[
        "Search and scrape information from https://www.themoviedb.org/ or https://www.imdb.com/ based on the given query.",
        "Provide results with the following details: movie title, genre, rating, description, recommended viewing age, primary language, "
        "and release date.",
        "Include trailers for movies similar to the recommendations and upcoming movies of the same genre or from related directors/actors.",
        "Present the output in a well-structured markdown table for readability.",
        "Avoid sharing direct links to movies or websites in the response.",
        "Ensure all movie data is current, especially for recent or upcoming releases."
    ],
    markdown=True,
)

movie_recommendation_agent.print_response(
    "Suggest four of the latest thriller movies released in 2024, including their ratings, genres, descriptions, and trailers for similar and upcoming movies.",
    stream=True
)
