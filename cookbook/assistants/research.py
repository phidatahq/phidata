from phi.assistant import Assistant
from phi.tools.duckduckgo import DuckDuckGo
from phi.tools.newspaper4k import Newspaper4k

assistant = Assistant(
    tools=[DuckDuckGo(), Newspaper4k()],
    show_tool_calls=True,
    description="You are a senior NYT researcher writing an article on a topic.",
    instructions=[
        "For the provided topic, search for the top 3 links.",
        "Then read each URL and extract the article text. If a URL isn't available, ignore and move on.",
        "Analyse and prepare an NYT worthy article based on the information.",
    ],
    add_datetime_to_instructions=True,
)
assistant.print_response("Latest developments in AI", markdown=True)
