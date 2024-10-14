from typing import Iterator  # noqa

from phi.agent import Agent, RunResponse  # noqa
from phi.model.openai import OpenAIChat
from phi.tools.duckduckgo import DuckDuckGo
from phi.tools.newspaper4k import Newspaper4k
from phi.utils.pprint import pprint_run_response  # noqa

agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    tools=[DuckDuckGo(), Newspaper4k()],
    description="You are a senior NYT researcher writing an article on a topic.",
    instructions=[
        "For a given topic, search for the top 5 links.",
        "Then read each URL and extract the article text, if a URL isn't available, ignore it.",
        "Analyse and prepare an NYT worthy article based on the information.",
    ],
    markdown=True,
    show_tool_calls=True,
    add_datetime_to_instructions=True,
    # debug_mode=True,
)

agent.print_response("Simulation theory", stream=True)

# Run agent and return the response as a stream
# response_stream: Iterator[RunResponse] = agent.run("Simulation theory", stream=True)
# Print the response stream in markdown format
# pprint_run_response(response_stream, markdown=True, show_time=True)

# Run agent and return the response as a variable
# response: RunResponse = agent.run("Simulation theory")
# Print the response in markdown format
# pprint_run_response(response, markdown=True)
