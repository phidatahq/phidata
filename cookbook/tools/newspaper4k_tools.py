from phi.agent import Agent
from phi.tools.newspaper4k import Newspaper4k

agent = Agent(tools=[Newspaper4k()], debug_mode=True, show_tool_calls=True)
agent.print_response(
    "https://www.rockymountaineer.com/blog/experience-icefields-parkway-scenic-drive-lifetime",
    markdown=True,
)
