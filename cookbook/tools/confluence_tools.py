from phi.agent import Agent
from phi.tools.confluence import ConfluenceTools


agent = Agent(
    name="Confluence agent",
    tools=[ConfluenceTools()],
    show_tool_calls=True,
    markdown=True,
)

## getting space details
agent.print_response("how many spaces are there , and what are its name?")

## getting page_content
agent.print_response("what is the content present in page Large language model in LLM space")

## getting page details in a particular space
agent.print_response("can you extract all the page names from LLM space")

## creating a new page in a space
agent.print_response("can you create a new page named TESTING in LLM space")
