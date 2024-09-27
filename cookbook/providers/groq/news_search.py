from phi.agent import Agent
from phi.model.groq import Groq
from phi.tools.duckduckgo import DuckDuckGo

agent = Agent(
    model=Groq(id="llama3-groq-70b-8192-tool-use-preview"),
    tools=[DuckDuckGo()],
    show_tool_calls=True,
    markdown=True,
)

agent.print_response("Provide the latest news on NVIDIA", stream=True)
