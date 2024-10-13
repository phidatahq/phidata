"""Please install dependencies using:
pip install openai duckduckgo-search newspaper4k lxml_html_clean phidata
"""

from phi.agent import Agent
from phi.tools.hackernews import HackerNews
from phi.tools.duckduckgo import DuckDuckGo
from phi.tools.newspaper4k import Newspaper4k


hn_researcher = Agent(
    name="HackerNews Researcher",
    role="Gets top stories from hackernews.",
    tools=[HackerNews()],
)

web_searcher = Agent(
    name="Web Searcher",
    role="Searches the web for information on a topic",
    tools=[DuckDuckGo()],
    add_datetime_to_instructions=True,
)

article_reader = Agent(
    name="Article Reader",
    role="Reads articles from URLs.",
    tools=[Newspaper4k()],
)

hn_team = Agent(
    name="Hackernews Team",
    team=[hn_researcher, web_searcher, article_reader],
    instructions=[
        "First, search hackernews for what the user is asking about.",
        "Next, ask the article reader to read the links for the stories to get more information.",
        "Important: you must provide the article reader with the links to read.",
        "Then, ask the web searcher to search for each story to get more information.",
        "Finally, provide a thoughtful and engaging summary.",
    ],
    show_tool_calls=True,
    markdown=True,
)
hn_team.print_response("Write an article about the top 2 stories on hackernews", stream=True)
