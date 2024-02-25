from os import getenv
from typing import Iterable, Optional

import vertexai
from vertexai.generative_models import GenerativeModel, GenerationResponse


def generate(project: Optional[str], location: Optional[str]) -> None:
    # Initialize Vertex AI
    vertexai.init(project=project, location=location)
    # Load the model
    model = GenerativeModel("gemini-1.0-pro-vision")
    # Query the model
    responses: Iterable[GenerationResponse] = model.generate_content("Who are you?", stream=True)
    # Process the response
    for response in responses:
        print(response.text, end="")
    print(" ")


# *********** Get project and location ***********
PROJECT_ID = getenv("PROJECT_ID")
LOCATION = getenv("LOCATION")

# *********** Run the example ***********
if __name__ == "__main__":
    generate(project=PROJECT_ID, location=LOCATION)
