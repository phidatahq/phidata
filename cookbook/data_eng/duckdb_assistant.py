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
    show_tool_calls=True,
    base_dir=Path(__file__).parent.joinpath("scratch"),
)

duckdb_assistant.cli_app(markdown=True)
