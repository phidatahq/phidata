import json
import asyncio
from phi.assistant.duckdb import DuckDbAssistant

data_analyst = DuckDbAssistant(
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
)

asyncio.run(data_analyst.async_print_response("What is the average rating of movies? Show me the SQL.", markdown=True))
