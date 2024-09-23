from phi.agent import Agent, RunResponse
from phi.model.azure import AzureOpenAIChat
from phi.tools.duckduckgo import DuckDuckGo

agent = Agent(
    model=AzureOpenAIChat(
        model="gpt-4o"
    ),
    tools=[DuckDuckGo()],
    show_tool_calls=True,
    # debug_mode=True,
)


# Return the result as a string
run: RunResponse = agent.run("Share a healthy breakfast recipe")  # type: ignore

print(run.content)
