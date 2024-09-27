from phi.assistant import Assistant
from phi.tools.googlesearch import GoogleSearch

news_assistant = Assistant(
    tools=[GoogleSearch()],
    description="You are a news assistant that helps users find the latest news.",
    instructions=[
        "Given a topic by the user, respond with 4 latest news items about that topic.",
        "Search for 10 news items and select the top 4 unique items.",
        "Search in English and in French.",
    ],
    show_tool_calls=True,
    debug_mode=True,
)

news_assistant.print_response("Mistral IA", markdown=True)
