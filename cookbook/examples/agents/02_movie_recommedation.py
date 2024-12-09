from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.tools.exa import ExaTools

movie_recommendation_agent = Agent(
    name="PopcornPal",
    tools=[
        ExaTools(), 
    ],
    model=OpenAIChat(id="gpt-4o"),
    description=(
        "You are PopcornPal, a movie recommendation agent that searches and scrapes movie websites to provide detailed recommendations, "
        "including ratings, genres, descriptions, trailers, and upcoming releases."
    ),
    instructions=[
        "Use Exa to search for the movies.",
        "Provide results with the following details: movie title, genre, good ratings, description, recommended viewing age, primary language, "
        "and release date.",
        "Include trailers for movies similar to the recommendations and upcoming movies of the same genre or from related directors/actors.",
        "Present the output in a well-structured markdown table for readability.",
        "Avoid sharing direct links to movies or websites in the response.",
        "Ensure all movie data is correct, especially for recent or upcoming releases."
    ],
    markdown=True,
)

movie_recommendation_agent.print_response(
    "Suggest four of the latest thriller movies released in 2024, including their ratings, genres, descriptions, and trailers for similar and upcoming movies.",
    stream=True
)
