from phi.assistant import Assistant
from phi.llm.cohere import CohereChat
from phi.tools.duckdb import DuckDbTools

duckdb_tools = DuckDbTools(create_tables=False, export_tables=False, summarize_tables=False)
duckdb_tools.create_table_from_path(
    path="https://phidata-public.s3.amazonaws.com/demo_data/IMDB-Movie-Data.csv", table="movies"
)

assistant = Assistant(
    llm=CohereChat(model="command-r-plus"),
    tools=[duckdb_tools],
    show_tool_calls=True,
    add_to_system_prompt="""
    Here are the tables you have access to:
    - movies: Contains information about movies from IMDB.
    """,
    # debug_mode=True,
)
assistant.print_response("What is the average rating of movies?", markdown=True, stream=False)
