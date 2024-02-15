from typing import List, Optional

from phi.assistant import Assistant
from phi.tools.duckduckgo import DuckDuckGo
from pydantic import BaseModel, Field
from rich.pretty import pprint


class NewsItem(BaseModel):
    position: int = Field(..., description="Rank of this news item.")
    title: Optional[str] = Field(None, description="Title of the news item.")
    link: Optional[str] = Field(None, description="Link to the news item.")
    snippet: Optional[str] = Field(None, description="Snippet of the news item.")
    source: Optional[str] = Field(None, description="Source of the news item.")
    date: Optional[str] = Field(None, description="Date of the news item.")
    thumbnail: Optional[str] = Field(None, description="Thumbnail of the news item.")


class NewsItems(BaseModel):
    items: List[NewsItem] = Field(..., description="List of news items.")


news_assistant = Assistant(
    tools=[DuckDuckGo(timeout=120)],
    # show_tool_calls=True,
    output_model=NewsItems,
    description="You are a news assistant that helps users find the latest news.",
    instructions=[
        "Given a topic by the user, respond with 2 latest news items about that topic.",
        "Make sure you provide only unique news items.",
        "Use the `duckduckgo_news` tool to get the latest news about a topic. "
        + "Search for 5 news items and select the top 10 unique items.",
    ],
    # Uncomment the line below to run the assistant in debug mode.
    # Useful when running the first time to see the tool calls.
    debug_mode=True,
)

# Note: This will take a while to run as it is fetching the latest news.
latest_news = news_assistant.run("US Stocks")
pprint(latest_news)
