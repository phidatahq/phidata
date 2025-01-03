"""Run `pip install duckduckgo-search openai` to install dependencies."""

from phi.agent import Agent
from phi.tools.duckduckgo import DuckDuckGo
from phi.storage.agent.json import JsonFileAgentStorage

agent = Agent(
    storage=JsonFileAgentStorage(dir_path="tmp/agent_sessions_json"),
    tools=[DuckDuckGo()],
    add_history_to_messages=True,
)
agent.print_response("How many people live in Canada?")
agent.print_response("What is their national anthem called?")
