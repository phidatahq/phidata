from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.tools.googleserper import SerperTool

serper_tool = SerperTool()

web_agent = Agent(
    name="Cricket News",
    model=OpenAIChat(id="gpt-4o"),
    tools=[serper_tool],
    instructions=["Always include sources"],
    show_tool_calls=True,
    markdown=True,
)
web_agent.print_response("how much run did Virat scored in 2nd Test Match against NZ in Kanpur", stream=True)