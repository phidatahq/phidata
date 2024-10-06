"""Run `pip install duckdb` to install dependencies."""

import os

from textwrap import dedent
from phi.agent import Agent
from phi.model.mistral import MistralChat
from phi.tools.duckdb import DuckDbTools

mistral_api_key = os.getenv("MISTRAL_API_KEY")

duckdb_tools = DuckDbTools(create_tables=False, export_tables=False, summarize_tables=False)
duckdb_tools.create_table_from_path(
    path="https://phidata-public.s3.amazonaws.com/demo_data/IMDB-Movie-Data.csv", table="movies"
)

agent = Agent(
    model=MistralChat(
        id="mistral-large-latest",
        api_key=mistral_api_key,
    ),
    tools=[duckdb_tools],
    markdown=True,
    show_tool_calls=True,
    additional_context=dedent("""\
    You have access to the following tables:
    - movies: Contains information about movies from IMDB.
    """),
)
agent.print_response("What is the average rating of movies?", stream=False)
