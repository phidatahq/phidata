from phi.agent import Agent, RunResponse
from phi.model.cohere import CohereChat
from phi.tools.duckduckgo import DuckDuckGo

agent = Agent(
    model=CohereChat(model="command-r-plus"),
    tools=[DuckDuckGo()],
    show_tool_calls=True,
    # debug_mode=True,
)


# Return the result as a string
run: RunResponse = agent.run("Share a healthy breakfast recipe")  # type: ignore

print(run.content)
