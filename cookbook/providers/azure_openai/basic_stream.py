import os
from typing import Iterator  # noqa

from dotenv import load_dotenv

from phi.agent import Agent, RunResponse  # noqa
from phi.model.azure import AzureOpenAIChat

load_dotenv()

azure_model = AzureOpenAIChat(
    id=os.getenv("AZURE_OPENAI_MODEL_NAME"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
)

agent = Agent(model=azure_model, instructions=["Respond in a southern tone"], markdown=True)

# Get the response in a variable
# run_response: Iterator[RunResponse] = agent.run("Explain simulation theory", stream=True)
# for chunk in run_response:
#     print(chunk.content)

# Print the response on the terminal
agent.print_response("Explain simulation theory", stream=True)
