"""Build a Data Analyst Agent using xAI."""

import json
from phi.model.xai import xAI
from phi.agent.duckdb import DuckDbAgent

data_analyst = DuckDbAgent(
    model=xAI(id="grok-beta"),
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
)
data_analyst.print_response(
    "Show me a histogram of ratings. "
    "Choose an appropriate bucket size but share how you chose it. "
    "Show me the result as a pretty ascii diagram",
    stream=True,
)
