from phi.agent import Agent
from phi.tools.hackernews import HackerNews

hn_agent = Agent(
    name="Hackernews Team",
    tools=[HackerNews()],
    show_tool_calls=True,
    markdown=True,
    # debug_mode=True,
)
hn_agent.print_response(
    "Write an engaging summary of the "
    "users with the top 2 stories on hackernews. "
    "Please mention the stories as well.",
)
