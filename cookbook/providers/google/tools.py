"""Run `pip install google-generativeai duckdb` to install dependencies."""

from pathlib import Path

from phi.agent import Agent
from phi.model.google import Gemini
import httpx

from phi.tools.csv_tools import CsvTools

# -*- Download the imdb csv for the assistant -*-
url = "https://phidata-public.s3.amazonaws.com/demo_data/IMDB-Movie-Data.csv"
response = httpx.get(url)
# Create a file in the wip dir which is ignored by git
imdb_csv = Path(__file__).parent.joinpath("wip").joinpath("imdb.csv")
imdb_csv.parent.mkdir(parents=True, exist_ok=True)
imdb_csv.write_bytes(response.content)


agent = Agent(
    model=Gemini(id="gemini-2.0-flash-exp"),
    tools=[CsvTools(csvs=[imdb_csv])],
    markdown=True,
)
agent.print_response("List all the csvs I provided.")
