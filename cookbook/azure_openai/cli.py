from phi.assistant import Assistant
from phi.llm.azure_openai import AzureOpenAIChat
import os

assistant = Assistant(
    llm=AzureOpenAIChat(
        azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT"),
        azure_deployment=os.environ.get("AZURE_DEPLOYMENT"),
        api_version=os.environ.get("OPENAI_API_VERSION"),
        api_key=os.environ.get("AZURE_OPENAI_API_KEY"),
    ),
    description="You help people with their health and fitness goals.")
assistant.cli_app(markdown=True)
