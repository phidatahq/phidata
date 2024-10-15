from phi.agent import Agent
from phi.tools.github import GithubTools

agent = Agent(
    instructions=[
        "Use your tools to answer questions about the repo: phidatahq/phidata",
        "Do not create any issues or pull requests unless explicitly asked to do so",
    ],
    tools=[GithubTools()],
    show_tool_calls=True,
)
agent.print_response("List open pull requests", markdown=True)
