from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.tools.duckduckgo import DuckDuckGo

web_agent = Agent(
    name="Web Agent",
    role="Search the web for information",
    model=OpenAIChat(id="gpt-4o"),
    tools=[DuckDuckGo()],
    instructions=["Always include sources"],
    show_tool_calls=True,
    markdown=True,
    respond_directly=True,
)

agent_team = Agent(
    team=[web_agent],
    instructions=["Always include sources", "Use tables to display data"],
    show_tool_calls=True,
    markdown=True,
    add_history_to_messages=True,
)

agent_team.print_response("Whats happening in the NY?", stream=True)
agent_team.print_response("Now tell me about the stock market.", stream=True)
