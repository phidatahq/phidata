"""Run `pip install duckdb` to install dependencies."""

import os
from textwrap import dedent

from dotenv import load_dotenv

from phi.agent import Agent
from phi.model.azure import AzureOpenAIChat
from phi.tools.duckdb import DuckDbTools


load_dotenv()

azure_model = AzureOpenAIChat(
    id=os.getenv("AZURE_OPENAI_MODEL_NAME"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
)

duckdb_tools = DuckDbTools(create_tables=False, export_tables=False, summarize_tables=False)
duckdb_tools.create_table_from_path(
    path="https://phidata-public.s3.amazonaws.com/demo_data/IMDB-Movie-Data.csv", table="movies"
)

agent = Agent(
    model=azure_model,
    tools=[duckdb_tools],
    markdown=True,
    show_tool_calls=True,
    additional_context=dedent("""\
    You have access to the following tables:
    - movies: Contains information about movies from IMDB.
    """),
)
agent.print_response("What is the average rating of movies?", stream=False)
