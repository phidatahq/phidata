from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.tools.yfinance import YFinanceTools
from phi.storage.agent.postgres import PgAgentStorage
from phi.playground import Playground

agent = Agent(
    name="Finance Agent",
    agent_id="finance-agent",
    model=OpenAIChat(id="gpt-4o"),
    tools=[YFinanceTools(enable_all_tools=True)],
    instructions=["Use tables where possible"],
    show_tool_calls=True,
    markdown=True,
    debug_mode=True,
    add_history_to_messages=True,
    description="You are a finance agent",
    add_datetime_to_instructions=True,
    storage=PgAgentStorage(table_name="agent_sessions", db_url="postgresql+psycopg://ai:ai@localhost:5532/ai"),
)
# agent.create_session()
# agent.print_response("What is the stock price of NVDA")

playground = Playground(agents=[agent])
app = playground.get_api_app()

if __name__ == "__main__":
    playground.serve("serve:app", reload=True)
    # uvicorn.run("serve:app", host="0.0.0.0", port=8000, reload=True)
