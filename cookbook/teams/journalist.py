"""
Inspired by the fantastic work by Matt Shumer (@mattshumer_): https://twitter.com/mattshumer_/status/1772286375817011259

Please run:
pip install openai anthropic google-search-results newspaper3k lxml_html_clean phidata
"""

from phi.assistant.team import Assistant
from phi.tools.serpapi_toolkit import SerpApiToolkit
from phi.tools.newspaper_toolkit import NewspaperToolkit
from phi.llm.anthropic import Claude


search_journalist = Assistant(
    name="Search Journalist",
    llm=Claude(model="claude-3-haiku-20240307"),
    role="Searches for top URLs based on a topic",
    description="You are a world-class search journalist. You search the web and retrieve the top URLs based on a topic.",
    instructions=[
        "Given a topic, conduct a search to find the top results.",
        "For a search topic, return the top 3 URLs.",
    ],
    tools=[SerpApiToolkit()],
    # debug_mode=True,
)
research_journalist = Assistant(
    name="Research Journalist",
    llm=Claude(model="claude-3-haiku-20240307"),
    role="Retrieves text from URLs",
    description="You are a world-class research journalist. You retrieve the text from the URLs.",
    instructions=["For a list of URLs, return the text of the articles."],
    tools=[NewspaperToolkit()],
    # debug_mode=True,
)

editor = Assistant(
    name="Editor",
    team=[search_journalist, research_journalist],
    description="You are a senior NYT editor. Given a topic, use the journalists to write a NYT worthy article.",
    instructions=[
        "Given a topic, ask the search journalist to search for the top 3 URLs.",
        "Then pass on these URLs to research journalist to get the text of the articles.",
        "Use the text of the articles to write an article about the topic.",
        "Make sure to write a well researched article with a clear and concise message.",
        "The article should be extremely articulate and well written. "
        "Focus on clarity, coherence, and overall quality.",
    ],
    # debug_mode=True,
    markdown=True,
)
editor.print_response("Write an article about latest developments in AI.")
