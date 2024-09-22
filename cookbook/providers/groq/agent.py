from phi.agent import Agent, RunResponse
from phi.model.groq import Groq
from phi.tools.duckduckgo import DuckDuckGo

agent = Agent(
    model=Groq(model="llama3-70b-8192"),
    tools=[DuckDuckGo()],
    show_tool_calls=True,
    # debug_mode=True,
)


# Return the result as a string
run: RunResponse = agent.run("Share a healthy breakfast recipe")  # type: ignore

print(run.content)
