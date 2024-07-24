import unittest

import timeout_decorator
from pydantic import BaseModel, Field

from phi.assistant import Assistant
from phi.llm.ollama import Ollama


class MovieScript(BaseModel):
    setting: str = Field(..., description="Provide a nice setting for a blockbuster movie.")
    ending: str = Field(..., description="Ending of the movie. If not available, provide a happy ending.")
    genre: str = Field(
        ..., description="Genre of the movie. If not available, select action, thriller or romantic comedy."
    )
    name: str = Field(..., description="Give a name to this movie")
    characters: list[str] = Field(..., description="Name of characters for this movie.")
    storyline: str = Field(..., description="3 sentence storyline for the movie. Make it exciting!")


class StructuredOutputTestCase(unittest.TestCase):
    @timeout_decorator.timeout(30)
    def test_something(self):
        assistant = Assistant(
            llm=Ollama(model="llama3.1"),
            description="You help write movie scripts.",
            output_model=MovieScript,
            debug_mode=True,
            monitoring=True,
        )

        result = assistant.run("New York", stream=False)
        self.assertNotIsInstance(result, str, msg="Ollama weak model against structured output.")
        self.assertIsInstance(result, MovieScript)

        result = assistant.run("New York", stream=True)
        self.assertNotIsInstance(result, str, msg="Ollama weak model against structured output.")
        self.assertIsInstance(result, MovieScript)


if __name__ == "__main__":
    unittest.main()
