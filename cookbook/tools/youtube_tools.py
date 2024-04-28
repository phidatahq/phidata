from phi.assistant import Assistant
from phi.tools.youtube_toolkit import YouTubeToolkit

assistant = Assistant(
    tools=[YouTubeToolkit()],
    show_tool_calls=True,
    description="You are a YouTube assistant. Obtain the captions of a YouTube video and answer questions.",
    debug_mode=True,
)
assistant.print_response("Summarize this video https://www.youtube.com/watch?v=Iv9dewmcFbs&t", markdown=True)
