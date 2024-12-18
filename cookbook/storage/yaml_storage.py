"""Run `pip install duckduckgo-search openai` to install dependencies."""

from phi.agent import Agent
from phi.tools.duckduckgo import DuckDuckGo
from phi.storage.agent.yaml import YamlFileAgentStorage

agent = Agent(
    storage=YamlFileAgentStorage(path="tmp/agent_sessions_yaml"),
    tools=[DuckDuckGo()],
    add_history_to_messages=True,
)
agent.print_response("How many people live in Canada?")
agent.print_response("What is their national anthem called?")
