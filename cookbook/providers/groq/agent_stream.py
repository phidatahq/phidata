from phi.agent import Agent
from phi.model.groq import Groq
from phi.tools.duckduckgo import DuckDuckGo

agent = Agent(
    model=Groq(model="llama3-70b-8192"),
    tools=[DuckDuckGo()],
    instructions=["respond in a southern accent"],
    show_tool_calls=True,
    debug_mode=True,
)

agent.print_response("Whats happening in France?", markdown=True, stream=True)
