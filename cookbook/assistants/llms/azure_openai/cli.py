from phi.assistant import Assistant
from phi.llm.azure import AzureOpenAIChat

assistant = Assistant(
    llm=AzureOpenAIChat(model="gpt-35-turbo"),  # model="deployment_name"
    description="You help people with their health and fitness goals.",
)
assistant.cli_app(markdown=True)
