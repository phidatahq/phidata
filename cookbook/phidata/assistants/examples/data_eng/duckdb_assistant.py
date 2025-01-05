import json
from pathlib import Path
from phi.assistant.duckdb import DuckDbAssistant

duckdb_assistant = DuckDbAssistant(
    semantic_model=json.dumps(
        {
            "tables": [
                {
                    "name": "movies",
                    "description": "Contains information about movies from IMDB.",
                    "path": "https://phidata-public.s3.amazonaws.com/demo_data/IMDB-Movie-Data.csv",
                }
            ]
        }
    ),
    markdown=True,
    show_tool_calls=True,
    base_dir=Path(__file__).parent.joinpath("scratch"),
)

# duckdb_assistant.cli_app()
duckdb_assistant.print_response("What is the average rating of movies? Show me the SQL?")
duckdb_assistant.print_response("Show me a histogram of movie ratings?")
duckdb_assistant.print_response("What are the top 5 movies?")
