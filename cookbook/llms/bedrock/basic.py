from phi.assistant import Assistant
from phi.llm.aws.claude import Claude

assistant = Assistant(
    llm=Claude(model="anthropic.claude-v2"),
    description="You help people with their health and fitness goals.",
    debug_mode=True,
)
assistant.print_response("Share a quick healthy breakfast recipe.", markdown=True, stream=False)
