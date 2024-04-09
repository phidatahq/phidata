from shutil import rmtree
from phi.assistant.team import Assistant
from phi.tools.serpapi_toolkit import SerpapiToolkit

from newspaper import Article

def get_article_text(url):
    """Get the text of an article from a URL.
    Args:
        url (str): The URL of the article.
    Returns:
        str: The text of the article.
    """
    article = Article(url)
    article.download()
    article.parse()
    return article.text


search_journalist = Assistant(
    name="Search Journalist",
    role="Searches for top URLs based on a topic",
    description="You are a world-class search journalist. You search the web and retreive the top URLs based on a topic.",
    instructions=[
        "Given a topic, conduct a search to find the top results.",
        "For a search topic, return the top 3 URLs.",
    ],
    tools=[SerpapiToolkit()],
    # debug_mode=True,
)

research_journalist = Assistant(
    name=" Research Journalist",
    role="Retrives text from URLs",
    description="You are a world-class research journalist. You retreive the text from the URLs.",
    instructions=["For a list of URLs, return the text of the articles."],
    tools=[get_article_text],
    # debug_mode=True,
)


editor = Assistant(
    name="Editor",
    team=[search_journalist, research_journalist],
    description="You are the senior editor. Given a topic, use the journalists to write a NYT worthy article.",
    instructions=[
        "Given a topic, ask the search journalist to search for the top 3 URLs.",
        "Then pass on these URLs to research journalist to get the text of the articles.",
        "Use the text of the articles to write an article about the topic.",
        "Make sure to write a well researched article with a clear and concise message.",
        "The article should be extremely articulate and well written. "
        "Focus on clarity, coherence, and overall quality.",
    ],
    debug_mode=True,
    markdown=True,
)

editor.print_response("Write an acticle about the Anthropic claude.")