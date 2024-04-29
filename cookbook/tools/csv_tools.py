import httpx
from pathlib import Path
from phi.assistant import Assistant
from phi.tools.csv_tools import CsvTools

# -*- Download the imdb csv for the assistant -*-
url = "https://phidata-public.s3.amazonaws.com/demo_data/IMDB-Movie-Data.csv"
response = httpx.get(url)
# Create a file in the wip dir which is ignored by git
imdb_csv = Path(__file__).parent.joinpath("wip").joinpath("imdb.csv")
imdb_csv.parent.mkdir(parents=True, exist_ok=True)
imdb_csv.write_bytes(response.content)

assistant = Assistant(
    tools=[CsvTools(csvs=[imdb_csv])],
    show_tool_calls=True,
    markdown=True,
    # debug_mode=True,
)
assistant.print_response(
    "First get the columns in the imdb file. After you've checked the columns then find the details about the movie 'Rogue One'"
)
