from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.tools.duckduckgo import DuckDuckGo

agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    tools=[DuckDuckGo()],
    show_tool_calls=True,
    read_chat_history=True,
    add_history_to_messages=True,
    num_history_responses=3,
    # add_history_to_messages_num=True,
    debug_mode=True,
)
agent.cli_app(markdown=True)
