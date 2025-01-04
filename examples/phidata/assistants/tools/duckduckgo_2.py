from phi.assistant import Assistant
from phi.tools.duckduckgo import DuckDuckGo


news_assistant = Assistant(
    tools=[DuckDuckGo()],
    description="You are a news assistant that helps users find the latest news.",
    instructions=[
        "Given a topic by the user, respond with 2 latest news items about that topic.",
        "Search for 5 news items and select the top 2 unique items.",
    ],
    show_tool_calls=True,
)

news_assistant.print_response("US Stocks", markdown=True)
