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

# # Example usage: Get pull request details
# agent.print_response("Get details of #1239", markdown=True)
# # Example usage: Get pull request changes
# agent.print_response("Show changes for #1239", markdown=True)
# # Example usage: List open issues
# agent.print_response("What is the latest opened issue?", markdown=True)
# # Example usage: Create an issue
# agent.print_response("Explain the comments for the most recent issue", markdown=True)
# # Example usage: Create a Repo
# agent.print_response("Create a repo called phi-test and add description hello", markdown=True)
