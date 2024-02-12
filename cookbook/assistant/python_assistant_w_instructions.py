from phi.assistant.python import PythonAssistant
from phi.file.local.csv import CsvFile
from rich.pretty import pprint
from pydantic import BaseModel, Field


class AssistantResponse(BaseModel):
    result: str = Field(..., description="The result of the users question.")


def average_rating() -> AssistantResponse:
    python_assistant = PythonAssistant(
        files=[
            CsvFile(
                path="https://phidata-public.s3.amazonaws.com/demo_data/IMDB-Movie-Data.csv",
                description="Contains information about movies from IMDB.",
            )
        ],
        instructions=[
            "Only provide the result, do not need to provide any additional information.",
        ],
        run_code=True,
        save_and_run=False,
        output_model=AssistantResponse,
        # Uncomment the following line to return result in markdown
        # markdown=True,
        # Uncomment the following line to let the assistant install python packages
        # pip_install=True,
        # Uncomment the following line to show debug logs
        # debug_mode=True,
    )

    response: AssistantResponse = python_assistant.run("What is the average rating of movies?")  # type: ignore
    return response


response: AssistantResponse = average_rating()

pprint(response)
# Output:
# AssistantResponse(result='6.7232')
