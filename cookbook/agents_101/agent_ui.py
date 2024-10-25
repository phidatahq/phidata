from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.tools.duckduckgo import DuckDuckGo
from phi.tools.yfinance import YFinanceTools
from phi.storage.agent.sqlite import SqlAgentStorage
from phi.playground import Playground, serve_playground_app

# Ortak yapılandırma parametreleri
common_config = {
    "model": OpenAIChat(id="gpt-4o"),
    "markdown": True,
    "storage": SqlAgentStorage(db_file="tmp/agents.db")
}

web_agent = Agent(
    name="Web Agent",
    agent_id="web_agent",
    role="Search the web for information",
    tools=[DuckDuckGo()],
    instructions=["Always include sources"],
    storage=SqlAgentStorage(table_name="web_agent_sessions", **common_config["storage"].__dict__),
    **{k:v for k,v in common_config.items() if k != "storage"}
)

finance_agent = Agent(
    name="Finance Agent", 
    agent_id="finance_agent",
    role="Get financial data",
    tools=[YFinanceTools(stock_price=True, analyst_recommendations=True, 
                        company_info=True, company_news=True)],
    instructions=["Always use tables to display data"],
    storage=SqlAgentStorage(table_name="finance_agent_sessions", **common_config["storage"].__dict__),
    **{k:v for k,v in common_config.items() if k != "storage"}
)

agent_team = Agent(
    name="Agent Team",
    agent_id="agent_team", 
    team=[web_agent, finance_agent],
    storage=SqlAgentStorage(table_name="agent_team_sessions", **common_config["storage"].__dict__),
    **{k:v for k,v in common_config.items() if k != "storage"}
)

app = Playground(agents=[finance_agent, web_agent, agent_team]).get_app()

if __name__ == "__main__":
    serve_playground_app("agent_ui:app", reload=True)
