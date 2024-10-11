"""Run `pip install yfinance exa_py` to install dependencies."""

from textwrap import dedent
from datetime import datetime

from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.tools.exa import ExaTools
from phi.tools.yfinance import YFinanceTools
from phi.storage.agent.postgres import PgAgentStorage
from phi.knowledge.pdf import PDFUrlKnowledgeBase
from phi.vectordb.pgvector import PgVector, SearchType
from phi.playground import Playground, serve_playground_app

db_url: str = "postgresql+psycopg://ai:ai@localhost:5532/ai"

finance_agent = Agent(
    name="Finance Agent",
    agent_id="finance-agent",
    model=OpenAIChat(id="gpt-4o"),
    tools=[YFinanceTools(enable_all=True)],
    instructions=["Use tables where possible"],
    show_tool_calls=True,
    markdown=True,
    debug_mode=True,
    add_history_to_messages=True,
    description="You are a finance agent",
    add_datetime_to_instructions=True,
    storage=PgAgentStorage(table_name="finance_agent_sessions", db_url=db_url),
)

research_agent = Agent(
    name="Research Agent",
    agent_id="research-agent",
    model=OpenAIChat(id="gpt-4o"),
    tools=[ExaTools(start_published_date=datetime.now().strftime("%Y-%m-%d"), type="keyword")],
    description=dedent("""\
    You are a Research Agent that has the special skill of writing New York Times worthy articles.
    If you can directly respond to the user, do so. If the user asks for a report or provides a topic, follow the instructions below.
    """),
    instructions=[
        "For the provided topic, run 3 different searches.",
        "Read the results carefully and prepare a NYT worthy article.",
        "Focus on facts and make sure to provide references.",
    ],
    expected_output=dedent("""\
    Your articles should be engaging, informative, well-structured and in markdown format. They should follow the following structure:

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
    storage=PgAgentStorage(table_name="research_agent_sessions", db_url=db_url),
)

recipe_knowledge_base = PDFUrlKnowledgeBase(
    urls=["https://phi-public.s3.amazonaws.com/recipes/ThaiRecipes.pdf"],
    vector_db=PgVector(table_name="thai_recipes", db_url=db_url, search_type=SearchType.hybrid),
)

recipe_agent = Agent(
    name="Recipe Agent",
    agent_id="recipe-agent",
    model=OpenAIChat(id="gpt-4o"),
    knowledge=recipe_knowledge_base,
    # Add a tool to read chat history.
    read_chat_history=True,
    show_tool_calls=True,
    markdown=True,
    debug_mode=True,
    storage=PgAgentStorage(table_name="recipe_agent_sessions", db_url=db_url),
)

app = Playground(agents=[finance_agent, research_agent, recipe_agent]).get_app()

if __name__ == "__main__":
    # Load the knowledge base: Comment out after first run
    # recipe_knowledge_base.load(upsert=True)
    serve_playground_app("serve:app", reload=True)
