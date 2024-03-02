from os import getenv
from typing import Optional

import vertexai
from vertexai.generative_models import GenerativeModel, Part


def multimodal_example(project: Optional[str], location: Optional[str]) -> str:
    # Initialize Vertex AI
    vertexai.init(project=project, location=location)
    # Load the model
    multimodal_model = GenerativeModel("gemini-1.0-pro-vision")
    # Query the model
    response = multimodal_model.generate_content(
        [
            # Add an example image
            Part.from_uri("gs://generativeai-downloads/images/scones.jpg", mime_type="image/jpeg"),
            # Add an example query
            "what is shown in this image?",
        ]
    )
    print("============= RESPONSE =============")
    print(response)
    print("============= RESPONSE =============")
    return response.text


# *********** Get project and location ***********
PROJECT_ID = getenv("PROJECT_ID")
LOCATION = getenv("LOCATION")

# *********** Run the example ***********
if __name__ == "__main__":
    result = multimodal_example(project=PROJECT_ID, location=LOCATION)
    print("============= RESULT =============")
    print(result)
    print("============= RESULT =============")
