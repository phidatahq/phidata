"""Run `pip install openai yfinance exa_py` to install dependencies."""

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
from phi.tools.models_labs import ModelsLabs
from phi.tools.dalle import Dalle

db_url: str = "postgresql+psycopg://ai:ai@localhost:5532/ai"

video_gen_agent = Agent(
    name="Video Gen Agent",
    agent_id="video-gen-agent",
    model=OpenAIChat(id="gpt-4o"),
    tools=[ModelsLabs()],
    markdown=True,
    debug_mode=True,
    show_tool_calls=True,
    instructions=[
        "You are an agent designed to generate videos using the VideoGen API.",
        "When asked to generate a video, use the generate_video function from the VideoGenTools.",
        "Only pass the 'prompt' parameter to the generate_video function unless specifically asked for other parameters.",
        "The VideoGen API returns an status and eta value, also display it in your response.",
        "After generating the video, return only the video URL from the API response.",
        "The VideoGen API returns an status and eta value, also display it in your response.",
        "Don't show fetch video, use the url in future_links in your response. Its GIF and use it in markdown format.",
    ],
    system_message="Do not modify any default parameters of the generate_video function unless explicitly specified in the user's request.",
    storage=PgAgentStorage(table_name="video_gen_agent", db_url=db_url),
)

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
    storage=PgAgentStorage(table_name="finance_agent", db_url=db_url),
)

dalle_agent = Agent(
    name="Dalle Agent",
    agent_id="dalle-agent",
    model=OpenAIChat(id="gpt-4o"),
    tools=[Dalle()],
    markdown=True,
    debug_mode=True,
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
    storage=PgAgentStorage(table_name="research_agent", db_url=db_url),
)

recipe_knowledge_base = PDFUrlKnowledgeBase(
    urls=["https://phi-public.s3.amazonaws.com/recipes/ThaiRecipes.pdf"],
    vector_db=PgVector(table_name="thai_recipes", db_url=db_url, search_type=SearchType.hybrid),
)

recipe_agent = Agent(
    name="Thai Recipes Agent",
    agent_id="thai-recipes-agent",
    model=OpenAIChat(id="gpt-4o"),
    knowledge=recipe_knowledge_base,
    description="You are an expert at Thai Recipes and have a knowledge base full of special Thai recipes.",
    instructions=["Search your knowledge base for thai recipes if needed."],
    # Add a tool to read chat history.
    read_chat_history=True,
    show_tool_calls=True,
    markdown=True,
    debug_mode=True,
    storage=PgAgentStorage(table_name="thai_recipe_agent", db_url=db_url),
)

app = Playground(agents=[finance_agent, research_agent, recipe_agent, dalle_agent, video_gen_agent]).get_app()

if __name__ == "__main__":
    # Load the knowledge base: Comment out after first run
    # recipe_knowledge_base.load(upsert=True)
    serve_playground_app("test:app", reload=True)
