from phi.agent import Agent, RunResponse
from phi.model.openai import OpenAIChat
from phi.tools.duckduckgo import DuckDuckGo

agent = Agent(
    model=OpenAIChat(model="gpt-4o"),
    tools=[DuckDuckGo()],
    show_tool_calls=True,
    # debug_mode=True,
)


# Return the result as a string
run: RunResponse = agent.run("Share a healthy breakfast recipe")  # type: ignore

print(run.content)
