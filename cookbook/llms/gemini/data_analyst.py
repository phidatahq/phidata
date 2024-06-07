import json
from textwrap import dedent
from os import getenv

import vertexai
from phi.assistant import Assistant
from phi.tools.duckdb import DuckDbTools
from phi.llm.gemini import Gemini

# *********** Initialize VertexAI ***********
vertexai.init(project=getenv("PROJECT_ID"), location=getenv("LOCATION"))

duckdb_assistant = Assistant(
    llm=Gemini(model="gemini-pro"),
    tools=[DuckDbTools()],
    description="You are an expert data engineer that writes DuckDb queries to analyze data.",
    instructions=[
        "Using the `semantic_model` below, find which tables and columns you need to accomplish the task.",
        "If you need to run a query, run `show_tables` to check the tables you need exist.",
        "If the tables do not exist, RUN `create_table_from_path` to create the table using the path from the `semantic_model`",
        "Once you have the tables and columns, create one single syntactically correct DuckDB query.",
        "If you need to join tables, check the `semantic_model` for the relationships between the tables.",
        "If the `semantic_model` contains a relationship between tables, use that relationship to join the tables even if the column names are different.",
        "Inspect the query using `inspect_query` to confirm it is correct.",
        "If the query is valid, RUN the query using the `run_query` function",
        "Analyse the results and return the answer to the user.",
        "Continue till you have accomplished the task.",
        "Show the user the SQL you ran",
    ],
    add_to_system_prompt=dedent(
        """
    You have access to the following semantic_model:
    <semantic_model>
    {}
    </semantic_model>
    """
    ).format(
        json.dumps(
            {
                "tables": [
                    {
                        "name": "movies",
                        "description": "Contains information about movies from IMDB.",
                        "path": "https://phidata-public.s3.amazonaws.com/demo_data/IMDB-Movie-Data.csv",
                    }
                ]
            }
        )
    ),
    show_tool_calls=True,
    debug_mode=True,
)

duckdb_assistant.print_response("What is the average rating of movies? Show me the SQL.", markdown=True)
