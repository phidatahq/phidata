from phi.agent import Agent
from phi.tools.hackernews import HackerNews


story_researcher = Agent(
    name="HackerNews Story Researcher",
    role="Researches hackernews stories and users.",
    tools=[HackerNews()],
)
user_researcher = Agent(
    name="HackerNews User Researcher",
    role="Reads articles from URLs.",
    tools=[HackerNews()],
)

hn_leader = Agent(
    name="Hackernews Team",
    team=[story_researcher, user_researcher],
    markdown=True,
    debug_mode=True,
)
hn_leader.print_response("Write a report about the users with the top 2 stories on hackernews", stream=True)
