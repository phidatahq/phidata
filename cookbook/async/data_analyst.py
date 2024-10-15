"""Run `pip install duckdb` to install dependencies."""

import asyncio
from textwrap import dedent
from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.tools.duckdb import DuckDbTools

duckdb_tools = DuckDbTools(create_tables=False, export_tables=False, summarize_tables=False)
duckdb_tools.create_table_from_path(
    path="https://phidata-public.s3.amazonaws.com/demo_data/IMDB-Movie-Data.csv", table="movies"
)

agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    tools=[duckdb_tools],
    markdown=True,
    show_tool_calls=True,
    additional_context=dedent("""\
    You have access to the following tables:
    - movies: contains information about movies from IMDB.
    """),
)
asyncio.run(agent.aprint_response("What is the average rating of movies?", stream=False))
