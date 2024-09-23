from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.tools.exa import ExaTools
from phi.tools.website import WebsiteTools

agent = Agent(
    model=OpenAIChat(model="gpt-4o"),
    tools=[ExaTools(), WebsiteTools()], 
    show_tool_calls=True
)
agent.print_response(
    "Produce this table: research chromatic homotopy theory."
    "Access each link in the result outputting the summary for that article, its link, and keywords; "
    "After the table output make conceptual ascii art of the overarching themes and constructions",
    markdown=True,
)
