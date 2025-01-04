from phi.assistant import Assistant
from phi.tools.newspaper4k import Newspaper4k

assistant = Assistant(tools=[Newspaper4k()], debug_mode=True, show_tool_calls=True)

assistant.print_response(
    "https://www.rockymountaineer.com/blog/experience-icefields-parkway-scenic-drive-lifetime",
    markdown=True,
)
