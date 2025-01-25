"""🎬 Movie Recommendation Agent - Your Personal Cinema Curator!

This example shows how to create an intelligent movie recommendation system that provides
comprehensive film suggestions based on your preferences. The agent combines movie databases,
ratings, reviews, and upcoming releases to deliver personalized movie recommendations.

Example prompts to try:
- "Suggest thriller movies similar to Inception and Shutter Island"
- "What are the top-rated comedy movies from the last 2 years?"
- "Find me Korean movies similar to Parasite and Oldboy"
- "Recommend family-friendly adventure movies with good ratings"
- "What are the upcoming superhero movies in the next 6 months?"

Run: `pip install openai exa_py agno` to install the dependencies
"""

from textwrap import dedent

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.exa import ExaTools

movie_recommendation_agent = Agent(
    name="PopcornPal",
    tools=[ExaTools()],
    model=OpenAIChat(id="gpt-4o"),
    description=dedent("""\
        You are PopcornPal, a passionate and knowledgeable film curator with expertise in cinema worldwide! 🎥

        Your mission is to help users discover their next favorite movies by providing detailed,
        personalized recommendations based on their preferences, viewing history, and the latest
        in cinema. You combine deep film knowledge with current ratings and reviews to suggest
        movies that will truly resonate with each viewer."""),
    instructions=(
        "Approach each recommendation with these steps:\n"
        "1. Analysis Phase\n"
        "   - Understand user preferences from their input\n"
        "   - Consider mentioned favorite movies' themes and styles\n"
        "   - Factor in any specific requirements (genre, rating, language)\n"
        "\n"
        "2. Search & Curate\n"
        "   - Use Exa to search for relevant movies\n"
        "   - Ensure diversity in recommendations\n"
        "   - Verify all movie data is current and accurate\n"
        "\n"
        "3. Detailed Information\n"
        "   - Movie title and release year\n"
        "   - Genre and subgenres\n"
        "   - IMDB rating (focus on 7.5+ rated films)\n"
        "   - Runtime and primary language\n"
        "   - Brief, engaging plot summary\n"
        "   - Content advisory/age rating\n"
        "   - Notable cast and director\n"
        "\n"
        "4. Extra Features\n"
        "   - Include relevant trailers when available\n"
        "   - Suggest upcoming releases in similar genres\n"
        "   - Mention streaming availability when known\n"
        "\n"
        "Presentation Style:\n"
        "- Use clear markdown formatting\n"
        "- Present main recommendations in a structured table\n"
        "- Group similar movies together\n"
        "- Add emoji indicators for genres (🎭 🎬 🎪)\n"
        "- Minimum 5 recommendations per query\n"
        "- Include a brief explanation for each recommendation"
    ),
    markdown=True,
    add_datetime_to_instructions=True,
    show_tool_calls=True,
)

# Example usage with different types of movie queries
movie_recommendation_agent.print_response(
    "Suggest some thriller movies to watch with a rating of 8 or above on IMDB. "
    "My previous favourite thriller movies are The Dark Knight, Venom, Parasite, Shutter Island.",
    stream=True,
)

# More example prompts to explore:
"""
Genre-specific queries:
1. "Find me psychological thrillers similar to Black Swan and Gone Girl"
2. "What are the best animated movies from Studio Ghibli?"
3. "Recommend some mind-bending sci-fi movies like Inception and Interstellar"
4. "What are the highest-rated crime documentaries from the last 5 years?"

International Cinema:
1. "Suggest Korean movies similar to Parasite and Train to Busan"
2. "What are the must-watch French films from the last decade?"
3. "Recommend Japanese animated movies for adults"
4. "Find me award-winning European drama films"

Family & Group Watching:
1. "What are good family movies for kids aged 8-12?"
2. "Suggest comedy movies perfect for a group movie night"
3. "Find educational documentaries suitable for teenagers"
4. "Recommend adventure movies that both adults and children would enjoy"

Upcoming Releases:
1. "What are the most anticipated movies coming out next month?"
2. "Show me upcoming superhero movie releases"
3. "What horror movies are releasing this Halloween season?"
4. "List upcoming book-to-movie adaptations"
"""
