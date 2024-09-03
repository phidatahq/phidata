from phi.assistant import Assistant
from phi.llm.together import Together

assistant = Assistant(
    llm=Together(model="meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo"),
    description="You help people with their health and fitness goals.",
)
assistant.print_response("Share a quick healthy breakfast recipe.", markdown=True)
