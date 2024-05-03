from phi.assistant import Assistant
from phi.llm.aws.claude import Claude

assistant = Assistant(
    llm=Claude(model="anthropic.claude-3-sonnet-20240229-v1:0"),
    description="You help people with their health and fitness goals.",
)
assistant.print_response("Share a quick healthy breakfast recipe.", markdown=True, stream=False)
