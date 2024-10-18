"""Run `pip install yfinance exa_py` to install dependencies."""

from textwrap import dedent
from datetime import datetime

from phi.agent import Agent
from phi.model.ollama import Ollama
from phi.tools.exa import ExaTools
from phi.tools.yfinance import YFinanceTools
from phi.storage.agent.postgres import PgAgentStorage
from phi.playground import Playground, serve_playground_app

db_url: str = "postgresql+psycopg://ai:ai@localhost:5532/ai"

finance_agent = Agent(
    name="Finance Agent",
    agent_id="finance-agent",
    model=Ollama(),
    tools=[YFinanceTools(enable_all=True)],
    instructions=["Use tables where possible"],
    show_tool_calls=True,
    markdown=True,
    debug_mode=True,
    add_history_to_messages=True,
    description="You are a finance agent",
    add_datetime_to_instructions=True,
    storage=PgAgentStorage(table_name="finance_agent_sessions_ollama", db_url=db_url),
)

research_agent = Agent(
    name="Research Agent",
    agent_id="research-agent",
    model=Ollama(),
    tools=[ExaTools(start_published_date=datetime.now().strftime("%Y-%m-%d"), type="keyword")],
    description="You are a Research Agent writing an article for the New York Times.",
    instructions=[
        "For the provided topic, run 3 different searches.",
        "Read the results carefully and prepare a NYT worthy article.",
        "Focus on facts and make sure to provide references.",
    ],
    expected_output=dedent("""\
    An engaging, informative, and well-structured article in markdown format:

    ## Engaging Article Title

    ### Overview
    {give a brief introduction of the article and why the user should read this report}
    {make this section engaging and create a hook for the reader}

    ### Section 1
    {break the article into sections}
    {provide details/facts/processes in this section}

    ... more sections as necessary...

    ### Takeaways
    {provide key takeaways from the article}

    ### References
    - [Reference 1](link)
    - [Reference 2](link)
    """),
    markdown=True,
    debug_mode=True,
    add_history_to_messages=True,
    add_datetime_to_instructions=True,
    storage=PgAgentStorage(table_name="research_agent_sessions_ollama", db_url=db_url),
)

app = Playground(agents=[finance_agent, research_agent]).get_app()

if __name__ == "__main__":
    serve_playground_app("ollama:app", port=8118, reload=True)
