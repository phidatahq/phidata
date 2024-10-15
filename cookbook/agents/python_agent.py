from pathlib import Path

from phi.agent.python import PythonAgent
from phi.model.openai import OpenAIChat
from phi.file.local.csv import CsvFile

cwd = Path(__file__).parent.resolve()
scratch_dir = cwd.joinpath("scratch")
if not scratch_dir.exists():
    scratch_dir.mkdir(exist_ok=True, parents=True)

python_agent = PythonAgent(
    model=OpenAIChat(id="gpt-4o"),
    base_dir=scratch_dir,
    files=[
        CsvFile(
            path="https://phidata-public.s3.amazonaws.com/demo_data/IMDB-Movie-Data.csv",
            description="Contains information about movies from IMDB.",
        )
    ],
    pip_install=True,
    show_tool_calls=True,
    debug_mode=True,
)

python_agent.print_response("What is the average rating of movies?", markdown=True)
