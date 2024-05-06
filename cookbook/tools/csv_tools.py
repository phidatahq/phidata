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
    markdown=True,
    show_tool_calls=True,
    instructions=[
        "First always get the list of files",
        "Then check the columns in the file",
        "Then run the query to answer the question",
    ],
    # debug_mode=True,
)
assistant.cli_app(stream=False)
