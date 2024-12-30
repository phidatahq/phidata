from phi.agent import Agent
from phi.tools.reddit import RedditTools

agent = Agent(
    instructions=[
        "Use your tools to answer questions about Reddit content and statistics",
        "Do not interact with posts or comments (no voting, commenting, or posting)",
        "Respect Reddit's content policies and NSFW restrictions",
        "When analyzing subreddits, provide relevant statistics and trends",
    ],
    tools=[RedditTools()],
    show_tool_calls=True,
)

agent.print_response("What are the top 5 posts on r/SAAS this week ?", stream=True)
