"""🎬 Movie Script Generator - Your AI Screenwriting Partner

This example shows how to use structured outputs with AI agents to generate
well-formatted movie script concepts. It shows two approaches:
1. JSON Mode: Traditional JSON response parsing
2. Structured Output: Enhanced structured data handling

Example prompts to try:
- "Tokyo" - Get a high-tech thriller set in futuristic Japan
- "Ancient Rome" - Experience an epic historical drama
- "Manhattan" - Explore a modern romantic comedy
- "Amazon Rainforest" - Adventure in an exotic location
- "Mars Colony" - Science fiction in a space settlement

Run `pip install openai agno` to install dependencies.
"""

from typing import List

from agno.agent import Agent, RunResponse  # noqa
from agno.models.openai import OpenAIChat
from pydantic import BaseModel, Field


class MovieScript(BaseModel):
    setting: str = Field(
        ...,
        description="A richly detailed, atmospheric description of the movie's primary location and time period. Include sensory details and mood.",
    )
    ending: str = Field(
        ...,
        description="The movie's powerful conclusion that ties together all plot threads. Should deliver emotional impact and satisfaction.",
    )
    genre: str = Field(
        ...,
        description="The film's primary and secondary genres (e.g., 'Sci-fi Thriller', 'Romantic Comedy'). Should align with setting and tone.",
    )
    name: str = Field(
        ...,
        description="An attention-grabbing, memorable title that captures the essence of the story and appeals to target audience.",
    )
    characters: List[str] = Field(
        ...,
        description="4-6 main characters with distinctive names and brief role descriptions (e.g., 'Sarah Chen - brilliant quantum physicist with a dark secret').",
    )
    storyline: str = Field(
        ...,
        description="A compelling three-sentence plot summary: Setup, Conflict, and Stakes. Hook readers with intrigue and emotion.",
    )


# Agent that uses JSON mode
json_mode_agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    description=(
        "You are an acclaimed Hollywood screenwriter known for creating unforgettable blockbusters! 🎬\n"
        "With the combined storytelling prowess of Christopher Nolan, Aaron Sorkin, and Quentin Tarantino, "
        "you craft unique stories that captivate audiences worldwide.\n\n"
        "Your specialty is turning locations into living, breathing characters that drive the narrative."
    ),
    instructions=(
        "When crafting movie concepts, follow these principles:\n\n"
        "1. Settings should be characters:\n"
        "   - Make locations come alive with sensory details\n"
        "   - Include atmospheric elements that affect the story\n"
        "   - Consider the time period's impact on the narrative\n\n"
        "2. Character Development:\n"
        "   - Give each character a unique voice and clear motivation\n"
        "   - Create compelling relationships and conflicts\n"
        "   - Ensure diverse representation and authentic backgrounds\n\n"
        "3. Story Structure:\n"
        "   - Begin with a hook that grabs attention\n"
        "   - Build tension through escalating conflicts\n"
        "   - Deliver surprising yet inevitable endings\n\n"
        "4. Genre Mastery:\n"
        "   - Embrace genre conventions while adding fresh twists\n"
        "   - Mix genres thoughtfully for unique combinations\n"
        "   - Maintain consistent tone throughout\n\n"
        "Transform every location into an unforgettable cinematic experience!"
    ),
    response_model=MovieScript,
)

# Agent that uses structured outputs
structured_output_agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    description=(
        "You are an acclaimed Hollywood screenwriter known for creating unforgettable blockbusters! 🎬\n"
        "With the combined storytelling prowess of Christopher Nolan, Aaron Sorkin, and Quentin Tarantino, "
        "you craft unique stories that captivate audiences worldwide.\n\n"
        "Your specialty is turning locations into living, breathing characters that drive the narrative."
    ),
    instructions=(
        "When crafting movie concepts, follow these principles:\n\n"
        "1. Settings should be characters:\n"
        "   - Make locations come alive with sensory details\n"
        "   - Include atmospheric elements that affect the story\n"
        "   - Consider the time period's impact on the narrative\n\n"
        "2. Character Development:\n"
        "   - Give each character a unique voice and clear motivation\n"
        "   - Create compelling relationships and conflicts\n"
        "   - Ensure diverse representation and authentic backgrounds\n\n"
        "3. Story Structure:\n"
        "   - Begin with a hook that grabs attention\n"
        "   - Build tension through escalating conflicts\n"
        "   - Deliver surprising yet inevitable endings\n\n"
        "4. Genre Mastery:\n"
        "   - Embrace genre conventions while adding fresh twists\n"
        "   - Mix genres thoughtfully for unique combinations\n"
        "   - Maintain consistent tone throughout\n\n"
        "Transform every location into an unforgettable cinematic experience!"
    ),
    response_model=MovieScript,
    structured_outputs=True,
)

# Example usage with different locations
json_mode_agent.print_response("Tokyo", stream=True)
structured_output_agent.print_response("Ancient Rome", stream=True)

# More examples to try:
"""
Creative location prompts to explore:
1. "Underwater Research Station" - For a claustrophobic sci-fi thriller
2. "Victorian London" - For a gothic mystery
3. "Dubai 2050" - For a futuristic heist movie
4. "Antarctic Research Base" - For a survival horror story
5. "Caribbean Island" - For a tropical adventure romance
"""

# To get the response in a variable:
# from rich.pretty import pprint

# json_mode_response: RunResponse = json_mode_agent.run("New York")
# pprint(json_mode_response.content)
# structured_output_response: RunResponse = structured_output_agent.run("New York")
# pprint(structured_output_response.content)